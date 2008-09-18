#! /usr/bin/env python

import os, py, sys
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile, mkdtemp
from string import atoi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import llmemory
from pypy.tool.gcc_cache import build_executable_cache_read, try_compile_cache
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.tool.cbuild import CompilationError
from pypy.tool.udir import udir
import distutils

# ____________________________________________________________
#
# Helpers for simple cases

def eci_from_header(c_header_source):
    return ExternalCompilationInfo(
        pre_include_bits=[c_header_source]
    )

def getstruct(name, c_header_source, interesting_fields):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        STRUCT = Struct(name, interesting_fields)
    return configure(CConfig)['STRUCT']

def getsimpletype(name, c_header_source, ctype_hint=rffi.INT):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        TYPE = SimpleType(name, ctype_hint)
    return configure(CConfig)['TYPE']

def getconstantinteger(name, c_header_source):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        CONST = ConstantInteger(name)
    return configure(CConfig)['CONST']

def getdefined(macro, c_header_source):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        DEFINED = Defined(macro)
    return configure(CConfig)['DEFINED']

def has(name, c_header_source):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        HAS = Has(name)
    return configure(CConfig)['HAS']

def verify_eci(eci):
    """Check if a given ExternalCompilationInfo compiles and links.
    If not, raises CompilationError."""
    class CConfig:
        _compilation_info_ = eci
        WORKS = Works()
    configure(CConfig)

def sizeof(name, eci, **kwds):
    class CConfig:
        _compilation_info_ = eci
        SIZE = SizeOf(name)
    for k, v in kwds.items():
        setattr(CConfig, k, v)
    return configure(CConfig)['SIZE']

def memory_alignment():
    """Return the alignment (in bytes) of memory allocations.
    This is enough to make sure a structure with pointers and 'double'
    fields is properly aligned."""
    global _memory_alignment
    if _memory_alignment is None:
        S = getstruct('struct memory_alignment_test', """
           struct memory_alignment_test {
               double d;
               void* p;
           };
        """, [])
        result = S._hints['align']
        assert result & (result-1) == 0, "not a power of two??"
        _memory_alignment = result
    return _memory_alignment
_memory_alignment = None

def getendianness(eci):
    if not hasattr(eci, 'endianness'):
        class CConfig:
            _compilation_info_ = eci
            DATA = ConstantString('(unsigned long int)0xFF')
        if configure(CConfig)['DATA'][0] == '\x00':
            eci.endianness = 'BE'
        else:
            eci.endianness = 'LE'
    return eci.endianness

# ____________________________________________________________
#
# General interface

class ConfigResult:
    def __init__(self, CConfig, info, entries):
        self.CConfig = CConfig
        self.result = {}
        self.info = info
        self.entries = entries
        
    def get_entry_result(self, entry):
        try:
            return self.result[entry]
        except KeyError:
            name = self.entries[entry]
            info = self.info[name]
            self.result[entry] = entry.build_result(info, self)
            return self.result[entry]

    def get_result(self):
        return dict([(name, self.result[entry])
                     for entry, name in self.entries.iteritems()])

class _CWriter(object):
    """ A simple class which aggregates config parts
    """
    def __init__(self, CConfig):
        self.path = uniquefilepath()
        self.f = self.path.open("w")
        self.config = CConfig

    def write_header(self):
        f = self.f
        CConfig = self.config
        CConfig._compilation_info_.write_c_header(f)
        print >> f, C_HEADER
        print >> f

    def write_entry(self, key, entry):
        f = self.f
        entry.key = key
        for line in entry.prepare_code():
            print >> f, line
        print >> f

    def start_main(self):
        print >> self.f, 'int main(int argc, char *argv[]) {'

    def close(self):
        f = self.f
        print >> f, '\treturn 0;'
        print >> f, '}'
        f.close()

    def ask_gcc(self, question):
        self.start_main()
        self.f.write(question + "\n")
        self.close()
        eci = self.config._compilation_info_
        try_compile_cache([self.path], eci)

def configure(CConfig):
    """Examine the local system by running the C compiler.
    The CConfig class contains CConfigEntry attribues that describe
    what should be inspected; configure() returns a dict mapping
    names to the results.
    """
    for attr in ['_includes_', '_libraries_', '_sources_', '_library_dirs_',
                 '_include_dirs_', '_header_']:
        assert not hasattr(CConfig, attr), "Found legacy attribute %s on CConfig" % (attr,)
    entries = []
    for key in dir(CConfig):
        value = getattr(CConfig, key)
        if isinstance(value, CConfigEntry):
            entries.append((key, value))

    if entries: # can be empty if there are only CConfigSingleEntries
        infolist = []
        writer = _CWriter(CConfig)
        writer.write_header()
        for key, entry in entries:
            writer.write_entry(key, entry)
        writer.start_main()
        writer.close()

        eci = CConfig._compilation_info_
        info = run_example_code(writer.path, eci)
        for key, entry in entries:
            entry.eci = eci
            if key in info:
                infolist.append(info[key])
            else:
                infolist.append({})
        assert len(infolist) == len(entries)
        resultinfo = {}
        resultentries = {}
        for info, (key, entry) in zip(infolist, entries):
            resultinfo[key] = info
            resultentries[entry] = key

        result = ConfigResult(CConfig, resultinfo, resultentries)
        for name, entry in entries:
            result.get_entry_result(entry)
        res = result.get_result()
    else:
        res = {}

    for key in dir(CConfig):
        value = getattr(CConfig, key)
        if isinstance(value, CConfigSingleEntry):
            writer = _CWriter(CConfig)
            writer.write_header()
            res[key] = value.question(writer.ask_gcc)
    
    for key in dir(CConfig):
        value = getattr(CConfig, key)
        if isinstance(value, CConfigExternEntry):
            value.eci = CConfig._compilation_info_
            res[key] = value.build_result(locals().get('result'))

    return res

# ____________________________________________________________

def c_safe_string(string):
    return string.replace('\\', '\\\\').replace('"', '\\"')

class CConfigEntry(object):
    "Abstract base class."
    def dump(self, name, expr):
        beginpad = "__START_PLATCHECK_%s\0%s\0" % (
            c_safe_string(self.key),
            c_safe_string(name))
        return '''
        struct __attribute__((packed)) {
            char begin_pad[%(sizeof_beginpad)i];
            typeof(%(expr)s) contents;
            char end_pad[];
        } pypy_test_%(id)s = {
            .begin_pad = "%(beginpad)s",
            .contents = %(expr)s,
            .end_pad = "__END_PLATCHECK__"
        };
        ''' % {'expr' : expr, 'beginpad' : beginpad.replace('\0', '\\0'),
                'sizeof_beginpad' : len(beginpad),
                'id' : filter(str.isalnum, self.key+'PLATCHECK'+name)}
    def dump_by_size(self, name, expr):
        beginpad = "__START_PLATCHECK_%s\0%s\0" % (
            c_safe_string(self.key),
            c_safe_string(name))
        return '''
        struct {
            char begin_pad[%(sizeof_beginpad)i];
            char contents[%(expr)s];
            char end_pad[];
        } pypy_test_%(id)s = {
            .begin_pad = "%(beginpad)s",
            .contents = {0},
            .end_pad = "__END_PLATCHECK__"
        };
        ''' % {'expr' : expr, 'beginpad' : beginpad.replace('\0', '\\0'),
                'sizeof_beginpad' : len(beginpad),
                'id' : filter(str.isalnum, self.key+'PLATCHECK'+name)}
    def dumpbool(self, name, expr):
        return self.dump(name, '((char)((%s)?1:0))' % (expr,))
    def bool(self, data):
        return data[0] != '\x00'

def get_symbol_data(eci, name, NM, OBJCOPY):
    link_extra = ' '.join(list(eci.link_extra) + ['-static', '-Wl,--trace', '-Wl,--whole-archive'])
    libraries = ' '.join(['-l' + lib for lib in eci.libraries])
    libdirs = ' '.join(['-L' + _dir for _dir in eci.library_dirs])
    dir = mkdtemp()
    srcpath = os.path.join(dir, 'main.c')
    objpath = os.path.join(dir, 'main.o')
    exepath = os.path.join(dir, 'main.exe')
    src = open(srcpath, 'w')
    src.write('int main() {}\n')
    src.close()
    if os.system('gcc -c -o %s %s' % (objpath, srcpath)):
        raise CompilationError('gcc does not work')
    linkcmd = ' '.join(['gcc -o ', exepath, objpath, link_extra, libdirs, libraries])
    link = Popen(linkcmd, shell=True, stdout=PIPE, stderr=PIPE)
    
    linked = []
    for line in link.stdout.readlines():
        line = line.strip()
        if os.path.exists(line):
            linked.append(line)
        sub = line.split('(')
        if len(sub) >= 2:
            sub = sub[1].split(')')[0].strip()
            if os.path.exists(sub) and sub not in linked:
                linked.append(sub)

    for obj in linked:
        nm = Popen(NM + ' -f sysv ' + obj, shell=True, stdout=PIPE, stderr=PIPE)
        nm = list(nm.stdout.readlines())
        is_archive = False
        for line in nm:
            if '[' in line and ']' in line:
                is_archive = True
                member = line.partition('[')[2].partition(']')[0]
                continue
            line = [part.strip() for part in line.split('|')]
            if len(line) == 7 and line[0] == name and line[2] != 'U':
                # only if the symbol is a real symbol .....^
                offset = atoi(line[1], 16)
                maxsize = atoi(line[4], 16)
                section = line[6]
                break
        else:
            continue
        base_offset = offset
        this_member = None
        for line in nm:
            if is_archive:
                if '[' in line and ']' in line:
                    this_member = line.partition('[')[2].partition(']')[0]
                    continue
            if not is_archive or this_member == member:
                line = [part.strip() for part in line.split('|')]
                if len(line) == 7 and line[6] == section and line[2] != 'U':
                    base_offset = min(base_offset, atoi(line[1], 16))
        offset = offset - base_offset
        break
    else:
        return None
    sec = NamedTemporaryFile()
    if is_archive:
        obj2 = NamedTemporaryFile()
        ar = Popen('ar p %s %s' % (obj, member), shell=True, stdout=PIPE)
        data = ar.stdout.read()
        obj2.write(data)
        obj2.flush()
        obj = obj2.name
    cmd = '%s -O binary -j \'%s\' %s %s' % (OBJCOPY, section, obj, sec.name)
    if os.system(cmd):
        raise CompilationError('objcopy error')
    sec.seek(offset)
    return sec.read(maxsize)

class CConfigExternEntry(object):
    """Abstract base class."""
    def get(self, name):
        return get_symbol_data(self.eci, name, 'nm', 'objcopy')

class ExternString(CConfigExternEntry):
    def __init__(self, name):
        self.name = name
    
    def build_result(self, config_result):
        data = self.get(self.name)
        if data:
            return data.partition('\0')[0]
        else:
            return None

class ExternStruct(CConfigExternEntry):
    def __init__(self, name, cconfig_entry=None, rffi_struct=None):
        if not (cconfig_entry or rffi_struct):
            raise TypeError('ExternStruct takes 3 arguments')
        self.entry = cconfig_entry
        self.rffi_struct = rffi_struct
        self.name = name
    
    def build_result(self, config_result):
        if not self.rffi_struct:
            rffi_struct = config_result.get_entry_result(self.entry)
        else:
            rffi_struct = self.rffi_struct
        data = self.get(self.name)
        if not data:
            return None
        class StructResult(object): pass
        res = StructResult()
        for (fld_name, fld_offset) in zip(
                rffi_struct._names, rffi_struct._hints['fieldoffsets']):
            fld_type = rffi_struct._flds[fld_name]
            fld_data = data[fld_offset:fld_offset+rffi.sizeof(fld_type)]
            setattr(res, fld_name, rffi.cast(fld_type, fld_data[0]))
        return res

class Struct(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined structure.
    """
    def __init__(self, name, interesting_fields, ifdef=None):
        self.name = name
        self.interesting_fields = interesting_fields
        self.ifdef = ifdef

    def prepare_code(self):
        if self.ifdef is not None:
            yield '#ifdef %s' % (self.ifdef,)
        platcheck_t = 'struct { char c; %s s; }' % (self.name,)
        if self.ifdef is not None:
            yield self.dumpbool("defined", '1')
        yield self.dump_by_size("align", 'offsetof(%s, s)' % (platcheck_t,))
        yield self.dump_by_size("size",  'sizeof(%s)' % (self.name,))
        for fieldname, fieldtype in self.interesting_fields:
            yield self.dump_by_size("fldofs " + fieldname, 'offsetof(%s, %s)' % (self.name, fieldname))
            yield self.dump_by_size("fldsize " + fieldname, 'sizeof(((%s*)0)->%s)' % (
                self.name, fieldname))
            if fieldtype in integer_class:
                yield self.dumpbool("fldunsigned " + fieldname, '((typeof(((%s*)0)->%s))(-1)) > 0' % (self.name, fieldname))
        if self.ifdef is not None:
            yield '#else'
            yield self.dumpbool("defined", '0')
            yield '#endif'

    def build_result(self, info, config_result):
        if self.ifdef is not None:
            if not self.bool(info['defined']):
                return None
        layout = [None] * len(info['size'])
        for fieldname, fieldtype in self.interesting_fields:
            if isinstance(fieldtype, Struct):
                offset = len(info['fldofs '  + fieldname])
                size   = len(info['fldsize ' + fieldname])
                c_fieldtype = config_result.get_entry_result(fieldtype)
                layout_addfield(layout, offset, c_fieldtype, fieldname)
            else:
                offset = len(info['fldofs '  + fieldname])
                size   = len(info['fldsize ' + fieldname])
                sign   = self.bool(info.get('fldunsigned ' + fieldname, '\0'))
                if (size, sign) != rffi.size_and_sign(fieldtype):
                    fieldtype = fixup_ctype(fieldtype, fieldname, (size, sign))
                layout_addfield(layout, offset, fieldtype, fieldname)

        n = 0
        padfields = []
        for i, cell in enumerate(layout):
            if cell is not None:
                continue
            name = '_pad%d' % (n,)
            layout_addfield(layout, i, rffi.UCHAR, name)
            padfields.append('c_' + name)
            n += 1

        # build the lltype Structure
        seen = {}
        fields = []
        fieldoffsets = []
        for offset, cell in enumerate(layout):
            if cell in seen:
                continue
            fields.append((cell.name, cell.ctype))
            fieldoffsets.append(offset)
            seen[cell] = True

        name = self.name
        hints = {'align': len(info['align']),
                 'size': len(info['size']),
                 'fieldoffsets': tuple(fieldoffsets),
                 'padding': tuple(padfields)}
        if name.startswith('struct '):
            name = name[7:]
        else:
            hints['typedef'] = True
        kwds = {'hints': hints}
        return rffi.CStruct(name, *fields, **kwds)

class SimpleType(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined simple numeric type.
    """
    def __init__(self, name, ctype_hint=rffi.INT, ifdef=None):
        self.name = name
        self.ctype_hint = ctype_hint
        self.ifdef = ifdef
    
    def prepare_code(self):
        if self.ifdef is not None:
            yield '#ifdef %s' % (self.ifdef,)
        if self.ifdef is not None:
            yield self.dumpbool("defined", '1')
        yield self.dump("size",  '((%s)0)' % (self.name,))
        if self.ctype_hint in integer_class:
            yield self.dumpbool("unsigned", '((%s)(-1)) > 0' % (self.name,))
        if self.ifdef is not None:
            yield '#else'
            yield self.dumpbool("defined", '0')
            yield '#endif'

    def build_result(self, info, config_result):
        if self.ifdef is not None and not self.bool(info['defined']):
            return None
        size = len(info['size'])
        sign = self.bool(info.get('unsigned', '\0'))
        ctype = self.ctype_hint
        if (size, sign) != rffi.size_and_sign(ctype):
            ctype = fixup_ctype(ctype, self.name, (size, sign))
        return ctype

def _load_int_le(data):
    result = 0
    for i in xrange(len(data)):
        result |= ord(data[i]) << (i*8)
    return result
def _load_int_be(data):
    result = 0
    for byte in data:
        result |= ord(byte)
        result <<= 8
    return result

class ConstantInteger(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined integer constant.
    """
    def __init__(self, name):
        self.name = name

    def prepare_code(self):
        yield self.dump('value', self.name)
        yield self.dump('negvalue', '-(%s)' % (self.name,))
        yield self.dump('positive', '(%s) >= 0' % (self.name,))

    def build_result(self, info, config_result):
        if self.bool(info['positive']):
            value = info['value']
        else:
            value = info['negvalue']
        if getendianness(self.eci) is 'BE':
            magnitude = _load_int_be(value)
        else:
            magnitude = _load_int_le(value)
        if self.bool(info['positive']):
            return magnitude
        else:
            return -magnitude

class ConstantString(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined string constant.
    """
    def __init__(self, name):
        self.name = name

    def prepare_code(self):
        yield self.dump('value', self.name)

    def build_result(self, info, config_result):
        return info['value']

class DefinedConstantInteger(ConstantInteger):
    """An entry in a CConfig class that stands for an externally
    defined integer constant. If not #defined the value will be None.
    """
    def __init__(self, macro):
        self.name = self.macro = macro

    def prepare_code(self):
        yield '#ifdef %s' % self.macro
        yield self.dumpbool('defined', '1')
        for line in ConstantInteger.prepare_code(self):
            yield line
        yield '#endif'

    def build_result(self, info, config_result):
        if 'defined' in info:
            return ConstantInteger.build_result(self, info, config_result)
        return None

class DefinedConstantString(CConfigEntry):
    """
    """
    def __init__(self, macro):
        self.macro = macro
        self.name = macro

    def prepare_code(self):
        yield '#ifdef %s' % (self.macro,)
        yield self.dump('macro', self.macro)
        yield '#endif'

    def build_result(self, info, config_result):
        if "macro" in info:
            return info["macro"]
        return None


class Defined(CConfigEntry):
    """A boolean, corresponding to an #ifdef.
    """
    def __init__(self, macro):
        self.macro = macro
        self.name = macro

    def prepare_code(self):
        yield '#ifdef %s' % (self.macro,)
        yield self.dumpbool("defined", '1')
        yield '#else'
        yield self.dumpbool("defined", '0')
        yield '#endif'

    def build_result(self, info, config_result):
        return self.bool(info['defined'])

class CConfigSingleEntry(object):
    """ An abstract class of type which requires
    gcc succeeding/failing instead of only asking
    """
    pass

class Has(CConfigSingleEntry):
    def __init__(self, name):
        self.name = name
    
    def question(self, ask_gcc):
        try:
            ask_gcc(self.name + ';')
            return True
        except CompilationError:
            return False

class Works(CConfigSingleEntry):
    def question(self, ask_gcc):
        ask_gcc("")

class SizeOf(CConfigEntry):
    """An entry in a CConfig class that stands for
    some external opaque type
    """
    def __init__(self, name):
        self.name = name

    def prepare_code(self):
        yield self.dump_by_size("size",  'sizeof(%s)' % (self.name,))

    def build_result(self, info, config_result):
        return len(info['size'])

# ____________________________________________________________
#
# internal helpers

def uniquefilepath(LAST=[0]):
    i = LAST[0]
    LAST[0] += 1
    return udir.join('platcheck_%d.c' % i)

integer_class = [rffi.SIGNEDCHAR, rffi.UCHAR, rffi.CHAR,
                 rffi.SHORT, rffi.USHORT,
                 rffi.INT, rffi.UINT,
                 rffi.LONG, rffi.ULONG,
                 rffi.LONGLONG, rffi.ULONGLONG]
# XXX SIZE_T?

float_class = [rffi.DOUBLE]

def _sizeof(tp):
    # XXX don't use this!  internal purpose only, not really a sane logic
    if isinstance(tp, lltype.Struct):
        return sum([_sizeof(i) for i in tp._flds.values()])
    return rffi.sizeof(tp)

class Field(object):
    def __init__(self, name, ctype):
        self.name = name
        self.ctype = ctype
    def __repr__(self):
        return '<field %s: %s>' % (self.name, self.ctype)

def layout_addfield(layout, offset, ctype, prefix):
    size = _sizeof(ctype)
    name = prefix
    i = 0
    while name in layout:
        i += 1
        name = '%s_%d' % (prefix, i)
    field = Field(name, ctype)
    for i in range(offset, offset+size):
        assert layout[i] is None, "%s overlaps %r" % (fieldname, layout[i])
        layout[i] = field
    return field

def fixup_ctype(fieldtype, fieldname, expected_size_and_sign):
    for typeclass in [integer_class, float_class]:
        if fieldtype in typeclass:
            for ctype in typeclass:
                if rffi.size_and_sign(ctype) == expected_size_and_sign:
                    return ctype
    if isinstance(fieldtype, lltype.FixedSizeArray):
        size, _ = expected_size_and_sign
        return lltype.FixedSizeArray(fieldtype.OF, size/_sizeof(fieldtype.OF))
    raise TypeError("conflicting field type %r for %r" % (fieldtype,
                                                          fieldname))


C_HEADER = """
#include <stddef.h>   /* for offsetof() */
"""

def run_example_code(filepath, eci):
    eci = eci.convert_sources_to_files(being_main=True)
    files = [filepath] + [py.path.local(f) for f in eci.separate_module_files]
    data = build_executable_cache_read(files, eci)
    
    end = 0
    section = {}
    while True:
        start = data.find('__START_PLATCHECK_', end)
        if start >= 0:
            start += len('__START_PLATCHECK_')
            keyend = data.find('\0', start)
            key = data[start:keyend]
            nameend = data.find('\0', keyend+1)
            name = data[keyend+1:nameend]
            start = nameend + 1
            end = data.find('__END_PLATCHECK__', start)
            if key in section:
                section[key][name] = data[start:end]
            else:
                section[key] = {name : data[start:end]}
        else:
            break
    return section

# ____________________________________________________________

def get_python_include_dir():
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    return gcv['INCLUDEPY']

if __name__ == '__main__':
    doc = """Example:
    
       rffi_platform.py  -h sys/types.h  -h netinet/in.h
                           'struct sockaddr_in'
                           sin_port  INT
    """
    import sys, getopt
    opts, args = getopt.gnu_getopt(sys.argv[1:], 'h:')
    if not args:
        print >> sys.stderr, doc
    else:
        assert len(args) % 2 == 1
        headers = []
        for opt, value in opts:
            if opt == '-h':
                headers.append('#include <%s>' % (value,))
        name = args[0]
        fields = []
        for i in range(1, len(args), 2):
            ctype = getattr(rffi, args[i+1])
            fields.append((args[i], ctype))

        S = getstruct(name, '\n'.join(headers), fields)

        for name in S._names:
            print name, getattr(S, name)
