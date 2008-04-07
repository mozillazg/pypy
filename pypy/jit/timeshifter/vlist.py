from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.timeshifter.rcontainer import VirtualContainer, FrozenContainer
from pypy.jit.timeshifter.rcontainer import cachedtype
from pypy.jit.timeshifter import rvalue, rvirtualizable, oop

from pypy.rpython.lltypesystem import lloperation
debug_print = lloperation.llop.debug_print

class NotConstInAVlist(Exception):
    pass

def TypeDesc(RGenOp, rtyper, exceptiondesc, LIST):
    if rtyper.type_system.name == 'lltypesystem':
        return LLTypeListTypeDesc(RGenOp, rtyper, exceptiondesc, LIST)
    else:
        return OOTypeListTypeDesc(RGenOp, rtyper, exceptiondesc, LIST)


class ItemDesc(object):
    __metaclass__ = cachedtype
    gcref = False
    canbevirtual = False

    def _freeze_(self):
        return True

    def __init__(self, ITEM):
        self.RESTYPE = ITEM
        if isinstance(ITEM, lltype.Ptr):
            T = ITEM.TO
            self.gcref = T._gckind == 'gc'
            if isinstance(T, lltype.ContainerType):
                if not T._is_varsize():
                    self.canbevirtual = True

class AbstractListTypeDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, RGenOp, rtyper, exceptiondesc, LIST):
        self.LIST = LIST
        self.LISTPTR = self.Ptr(LIST)
        self.ptrkind = RGenOp.kindToken(self.LISTPTR)
        self.null = self.LISTPTR._defl()
        self.gv_null = RGenOp.constPrebuiltGlobal(self.null)
        self.exceptiondesc = exceptiondesc

        self._setup(RGenOp, rtyper, LIST)
        self._define_devirtualize()
        self._define_allocate()

    def _define_allocate(self):
        LIST = self.LIST
        LISTPTR = self.LISTPTR

        def allocate(rgenop, n):
            l = LIST.ll_newlist(n)
            return rgenop.genconst(l)

        def populate(item_boxes, gv_lst, box_gv_reader):
            l = gv_lst.revealconst(LISTPTR)
            # NB. len(item_boxes) may be l.ll_length()+1 if need_reshaping :-(
            for i in range(l.ll_length()):
                box = item_boxes[i]
                if box is not None:
                    gv_value = box_gv_reader(box)
                    if gv_value.is_const:
                        v = gv_value.revealconst(LIST.ITEM)
                        l.ll_setitem_fast(i, v)
                    else:
                        raise NotConstInAVlist("Cannot put variable to a vlist")

        self.allocate = allocate
        self.populate = populate

    def _freeze_(self):
        return True

    def factory(self, length, itembox):
        vlist = VirtualList(self, length, itembox)
        box = self.PtrRedBox(known_nonzero=True)
        box.content = vlist
        vlist.ownbox = box
        return box


class LLTypeListTypeDesc(AbstractListTypeDesc):

    Ptr = staticmethod(lltype.Ptr)
    PtrRedBox = rvalue.PtrRedBox

    def _setup(self, RGenOp, rtyper, LIST):
        argtypes = [lltype.Signed]
        ll_newlist_ptr = rtyper.annotate_helper_fn(LIST.ll_newlist,
                                                   argtypes)
        self.gv_ll_newlist = RGenOp.constPrebuiltGlobal(ll_newlist_ptr)
        self.tok_ll_newlist = RGenOp.sigToken(lltype.typeOf(ll_newlist_ptr).TO)

        argtypes = [self.LISTPTR, lltype.Signed, LIST.ITEM]
        ll_setitem_fast = rtyper.annotate_helper_fn(LIST.ll_setitem_fast,
                                                    argtypes)
        self.gv_ll_setitem_fast = RGenOp.constPrebuiltGlobal(ll_setitem_fast)
        self.tok_ll_setitem_fast = RGenOp.sigToken(
            lltype.typeOf(ll_setitem_fast).TO)

    def _define_devirtualize(self):
        LIST = self.LIST
        LISTPTR = self.LISTPTR
        itemdesc = ItemDesc(LIST.ITEM)

        def make(vrti):
            n = len(vrti.varindexes)
            l = LIST.ll_newlist(n)
            return lltype.cast_opaque_ptr(llmemory.GCREF, l)
        
        def fill_into(vablerti, l, base, vrti):
            l = lltype.cast_opaque_ptr(LISTPTR, l)
            n = len(vrti.varindexes)
            for i in range(n):
                v = vrti._read_field(vablerti, itemdesc, base, i)
                l.ll_setitem_fast(i, v)

        self.devirtualize = make, fill_into

    def gen_newlist(self, builder, args_gv):
        return builder.genop_call(self.tok_ll_newlist,
                                  self.gv_ll_newlist,
                                  args_gv)

    def gen_setitem_fast(self, builder, args_gv):
        return builder.genop_call(self.tok_ll_setitem_fast,
                                  self.gv_ll_setitem_fast,
                                  args_gv)

        

class OOTypeListTypeDesc(AbstractListTypeDesc):

    Ptr = staticmethod(lambda T: T)
    PtrRedBox = rvalue.InstanceRedBox

    def _setup(self, RGenOp, rtyper, LIST):
        self.alloctoken = RGenOp.allocToken(LIST)
        self.tok_ll_resize = RGenOp.methToken(LIST, '_ll_resize')
        self.tok_ll_setitem_fast = RGenOp.methToken(LIST,
                                                    'll_setitem_fast')

    def _define_devirtualize(self):
        pass # XXX

    def gen_newlist(self, builder, args_gv):
        gv_lst = builder.genop_new(self.alloctoken)
        builder.genop_oosend(self.tok_ll_resize, gv_lst, args_gv)
        return gv_lst

    def gen_setitem_fast(self, builder, args_gv):
        gv_lst = args_gv.pop(0)
        return builder.genop_oosend(self.tok_ll_setitem_fast,
                                    gv_lst, args_gv)

class FrozenVirtualList(FrozenContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.fz_item_boxes initialized later

    def exactmatch(self, vlist, outgoingvarboxes, memo):
        assert isinstance(vlist, VirtualList)
        contmemo = memo.containers
        if self in contmemo:
            ok = vlist is contmemo[self]
            if not ok:
                outgoingvarboxes.append(vlist.ownbox)
            return ok
        if vlist in contmemo:
            assert contmemo[vlist] is not self
            outgoingvarboxes.append(vlist.ownbox)
            return False
        assert self.typedesc is vlist.typedesc
        self_boxes = self.fz_item_boxes
        vlist_boxes = vlist.item_boxes
        if len(self_boxes) != len(vlist_boxes):
            outgoingvarboxes.append(vlist.ownbox)
            return False
        contmemo[self] = vlist
        contmemo[vlist] = self
        fullmatch = True
        for i in range(len(self_boxes)):
            if not self_boxes[i].exactmatch(vlist_boxes[i],
                                            outgoingvarboxes,
                                            memo):
                fullmatch = False
        return fullmatch

    def unfreeze(self, incomingvarboxes, memo):
        contmemo = memo.containers
        if self in contmemo:
            return contmemo[self]
        typedesc = self.typedesc
        self_boxes = self.fz_item_boxes
        length = len(self_boxes)
        ownbox = typedesc.factory(length, None)
        contmemo[self] = ownbox
        vlist = ownbox.content
        assert isinstance(vlist, VirtualList)
        for i in range(length):
            fz_box = self_boxes[i]
            vlist.item_boxes[i] = fz_box.unfreeze(incomingvarboxes,
                                                  memo)
        return ownbox



class VirtualList(VirtualContainer):

    allowed_in_virtualizable = True

    def __init__(self, typedesc, length=0, itembox=None):
        self.typedesc = typedesc
        self.itembox = itembox
        self.item_boxes = [itembox] * length
        # self.ownbox = ...    set in factory()

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.item_boxes:
                box.enter_block(incoming, memo)

    def setforced(self, gv_forced):
        self.item_boxes = None
        self.ownbox.setgenvar_hint(gv_forced, known_nonzero=True)
        self.ownbox.content = None        

    def force_runtime_container(self, jitstate):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        boxes = self.item_boxes
        self.item_boxes = None

        debug_print(lltype.Void, "FORCE LIST (%d items)" % (len(boxes),))
        args_gv = [builder.rgenop.genconst(len(boxes))]
        gv_list = typedesc.gen_newlist(builder, args_gv)
        self.setforced(gv_list)

        for i in range(len(boxes)):
            gv_item = boxes[i].getgenvar(jitstate)
            args_gv = [gv_list, builder.rgenop.genconst(i), gv_item]
            typedesc.gen_setitem_fast(builder, args_gv)

    def freeze(self, memo):
        contmemo = memo.containers
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = FrozenVirtualList(self.typedesc)
            frozens = [box.freeze(memo) for box in self.item_boxes]
            result.fz_item_boxes = frozens
            return result

    def copy(self, memo):
        contmemo = memo.containers
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = VirtualList(self.typedesc)
            result.item_boxes = [box.copy(memo)
                                 for box in self.item_boxes]
            result.ownbox = self.ownbox.copy(memo)
            return result

    def replace(self, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for i in range(len(self.item_boxes)):
                self.item_boxes[i] = self.item_boxes[i].replace(memo)
            self.ownbox = self.ownbox.replace(memo)


    def make_rti(self, jitstate, memo):
        try:
            return memo.containers[self]
        except KeyError:
            pass
        typedesc = self.typedesc
        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        rgenop = jitstate.curbuilder.rgenop
        vrti = rvirtualizable.VirtualRTI(rgenop, bitmask)
        vrti.devirtualize = typedesc.devirtualize
        memo.containers[self] = vrti

        builder = jitstate.curbuilder
        place = builder.alloc_frame_place(typedesc.ptrkind)
        vrti.forced_place = place
        forced_box = rvalue.PtrRedBox()
        memo.forced_boxes.append((forced_box, place))

        vars_gv = memo.framevars_gv
        varindexes = vrti.varindexes
        vrtis = vrti.vrtis
        j = -1
        for box in self.item_boxes:
            if box.genvar:
                varindexes.append(memo.frameindex)
                memo.frameindex += 1
                vars_gv.append(box.genvar)
            else:
                varindexes.append(j)
                assert isinstance(box, rvalue.AbstractPtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                vrtis.append(content.make_rti(jitstate, memo))
                j -= 1

        self.item_boxes.append(forced_box)
        return vrti

    def reshape(self, jitstate, shapemask, memo):
        if self in memo.containers:
            return
        typedesc = self.typedesc
        builder = jitstate.curbuilder        
        memo.containers[self] = None
        bitmask = 1<<memo.bitcount
        memo.bitcount += 1

        boxes = self.item_boxes
        outside_box = boxes.pop()
        if bitmask&shapemask:
            gv_forced = outside_box.genvar
            memo.forced.append((self, gv_forced))
            
        for box in boxes:
            if not box.genvar:
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.reshape(jitstate, shapemask, memo)

    def store_back_gv_reshaped(self, shapemask, memo):
        if self in memo.containers:
            return
        typedesc = self.typedesc
        memo.containers[self] = None
        bitmask = 1<<memo.bitcount
        memo.bitcount += 1

        boxes = self.item_boxes
        outside_box = boxes[-1]
        if bitmask&shapemask:
            gv_forced = memo.box_gv_reader(outside_box)
            memo.forced_containers_gv[self] = gv_forced
            
        for box in boxes:
            if not box.genvar:
                assert isinstance(box, rvalue.AbstractPtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.store_back_gv_reshaped(shapemask, memo)

    def allocate_gv_container(self, rgenop, need_reshaping=False):
        length = len(self.item_boxes)
        if need_reshaping:
            length -= 1      # hack hack hack
        return self.typedesc.allocate(rgenop, length)

    def populate_gv_container(self, rgenop, gv_listptr, box_gv_reader):
        self.typedesc.populate(self.item_boxes, gv_listptr, box_gv_reader)


def oop_newlist(jitstate, oopspecdesc, deepfrozen, lengthbox, itembox=None):
    if lengthbox.is_constant():
        length = rvalue.ll_getvalue(lengthbox, lltype.Signed)
        return oopspecdesc.typedesc.factory(length, itembox)
    return oopspecdesc.residual_call(jitstate, [lengthbox, itembox])

def oop_list_copy(jitstate, oopspecdesc, deepfrozen, selfbox):
    content = selfbox.content
    if isinstance(content, VirtualList):
        copybox = oopspecdesc.typedesc.factory(0, None)
        copycontent = copybox.content
        assert isinstance(copycontent, VirtualList)
        copycontent.item_boxes.extend(content.item_boxes)
        return copybox
    else:
        return oopspecdesc.residual_call(jitstate, [selfbox])

def oop_list_len(jitstate, oopspecdesc, deepfrozen, selfbox):
    content = selfbox.content
    if isinstance(content, VirtualList):
        return rvalue.ll_fromvalue(jitstate, len(content.item_boxes))
    else:
        return oopspecdesc.residual_call(jitstate, [selfbox],
                                         deepfrozen=deepfrozen)
oop_list_len.couldfold = True

def oop_list_nonzero(jitstate, oopspecdesc, deepfrozen, selfbox):
    content = selfbox.content
    if isinstance(content, VirtualList):
        return rvalue.ll_fromvalue(jitstate, bool(content.item_boxes))
    else:
        return oopspecdesc.residual_call(jitstate, [selfbox],
                                         deepfrozen=deepfrozen)
oop_list_nonzero.couldfold = True

def oop_list_method_resize(jitstate, oopspecdesc, deepfrozen, selfbox, lengthbox):
    # only used by ootypesystem
    content = selfbox.content
    if isinstance(content, VirtualList):
        item_boxes = content.item_boxes
        # I think this is always true, better to assert it
        assert lengthbox.is_constant()
        length = rvalue.ll_getvalue(lengthbox, lltype.Signed)
        if len(item_boxes) < length:
            diff = length - len(item_boxes)
            item_boxes += [content.itembox] * diff
        elif len(item_boxes) > length:
            assert False, 'XXX'
    else:
        oopspecdesc.residual_call(jitstate, [selfbox],
                                  deepfrozen=deepfrozen)

def oop_list_append(jitstate, oopspecdesc, deepfrozen, selfbox, itembox):
    content = selfbox.content
    if isinstance(content, VirtualList):
        content.item_boxes.append(itembox)
    else:
        oopspecdesc.residual_call(jitstate, [selfbox, itembox])

def oop_list_insert(jitstate, oopspecdesc, deepfrozen, selfbox, indexbox, itembox):
    content = selfbox.content
    if isinstance(content, VirtualList) and indexbox.is_constant():
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        # XXX what if the assert fails?
        assert 0 <= index <= len(content.item_boxes)
        content.item_boxes.insert(index, itembox)
    else:
        oopspecdesc.residual_call(jitstate, [selfbox, indexbox, itembox])

def oop_list_concat(jitstate, oopspecdesc, deepfrozen, selfbox, otherbox):
    content = selfbox.content
    if isinstance(content, VirtualList):
        assert isinstance(otherbox, rvalue.AbstractPtrRedBox)
        othercontent = otherbox.content
        if othercontent is not None and isinstance(othercontent, VirtualList):
            newbox = oopspecdesc.typedesc.factory(0, None)
            newcontent = newbox.content
            assert isinstance(newcontent, VirtualList)
            newcontent.item_boxes.extend(content.item_boxes)
            newcontent.item_boxes.extend(othercontent.item_boxes)
            return newbox
    return oopspecdesc.residual_call(jitstate, [selfbox, otherbox])

def oop_list_pop(jitstate, oopspecdesc, deepfrozen, selfbox, indexbox=None):
    content = selfbox.content
    if indexbox is None:
        if isinstance(content, VirtualList):
            try:
                return content.item_boxes.pop()
            except IndexError:
                return oopspecdesc.residual_exception(jitstate, IndexError)
        else:
            return oopspecdesc.residual_call(jitstate, [selfbox])

    if (isinstance(content, VirtualList) and
        indexbox.is_constant()):
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        try:
            return content.item_boxes.pop(index)
        except IndexError:
            return oopspecdesc.residual_exception(jitstate, IndexError)
    return oopspecdesc.residual_call(jitstate, [selfbox, indexbox])

def oop_list_reverse(jitstate, oopspecdesc, deepfrozen, selfbox):
    content = selfbox.content
    if isinstance(content, VirtualList):
        content.item_boxes.reverse()
    else:
        oopspecdesc.residual_call(jitstate, [selfbox])

def oop_list_getitem(jitstate, oopspecdesc, deepfrozen, selfbox, indexbox):
    content = selfbox.content
    if isinstance(content, VirtualList) and indexbox.is_constant():
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        try:
            return content.item_boxes[index]
        except IndexError:
            return oopspecdesc.residual_exception(jitstate, IndexError)
    else:
        return oopspecdesc.residual_call(jitstate, [selfbox, indexbox],
                                         deepfrozen=deepfrozen)
oop_list_getitem.couldfold = True

def oop_list_setitem(jitstate, oopspecdesc, deepfrozen, selfbox, indexbox, itembox):
    content = selfbox.content
    if isinstance(content, VirtualList) and indexbox.is_constant():
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        try:
            content.item_boxes[index] = itembox
        except IndexError:
            oopspecdesc.residual_exception(jitstate, IndexError)
    else:
        oopspecdesc.residual_call(jitstate, [selfbox, indexbox, itembox])

oop_list_method_setitem_fast = oop_list_setitem

def oop_list_delitem(jitstate, oopspecdesc, deepfrozen, selfbox, indexbox):
    content = selfbox.content
    if isinstance(content, VirtualList) and indexbox.is_constant():
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        try:
            del content.item_boxes[index]
        except IndexError:
            oopspecdesc.residual_exception(jitstate, IndexError)
    else:
        oopspecdesc.residual_call(jitstate, [selfbox, indexbox])
