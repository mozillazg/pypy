import py
import sys
from pypy.interpreter.gateway import ApplevelClass 
from pypy.interpreter.error import OperationError
from pypy.tool import pytestsupport
from pypy.interpreter.module import Module as PyPyModule 
from pypy.interpreter.main import run_string, run_file

# the following adds command line options as a side effect! 
from pypy.conftest import gettestobjspace, option
from test.regrtest import reportdiff

# 
# Interfacing/Integrating with py.test's collection process 
#

# XXX no nice way to implement a --listpassing py.test option?! 
#option = py.test.addoptions("compliance testing options", 
#    py.test.Option('-L', '--listpassing', action="store", default=None, 
#                   type="string", dest="listpassing", 
#                   help="display only the list of expected-to-pass tests.")

mydir = py.magic.autopath().dirpath()

def make_module(space, dottedname, filepath): 
    #print "making module", dottedname, "from", filepath 
    w_dottedname = space.wrap(dottedname) 
    mod = PyPyModule(space, w_dottedname) 
    w_globals = mod.w_dict 
    w_filename = space.wrap(str(filepath)) 
    w_execfile = space.builtin.get('execfile') 
    space.call_function(w_execfile, w_filename, w_globals, w_globals)
    w_mod = space.wrap(mod) 
    w_modules = space.sys.get('modules') 
    space.setitem(w_modules, w_dottedname, w_mod) 
    return w_mod 

def callex(space, func, *args, **kwargs): 
    try: 
        return func(*args, **kwargs) 
    except OperationError, e: 
        if e.match(space, space.w_KeyboardInterrupt): 
            raise KeyboardInterrupt 
        raise
    
class RegrDirectory(py.test.collect.Directory): 
    def run(self): 
        l = []
        for (name, (enabled, typ)) in testmap.items(): 
            if enabled: 
                l.append(name) 
        return l 

    def join(self, name): 
        if name not in testmap: 
            raise NameError(name) 
        enabled, typ = testmap[name]
        return typ(name, parent=self) 

Directory = RegrDirectory

w_testlist = None 

def hack_test_support(space): 
    global w_testlist  
    w_testlist = space.newlist([]) 
    space.appexec([w_testlist], """
        (testlist): 
            def hack_run_unittest(*classes): 
                testlist.extend(list(classes))
            from test import test_support  # humpf
            test_support.run_unittest = hack_run_unittest 
    """) 

def getmyspace(): 
    space = gettestobjspace('std') 
    # we once and for all want to patch run_unittest 
    # to get us the list of intended unittest-TestClasses
    # from each regression test 
    if w_testlist is None: 
        callex(space, hack_test_support, space) 
    return space 

app = ApplevelClass('''
    #NOT_RPYTHON  

    def list_testmethods(cls): 
        """ return [(instance.setUp, instance.tearDown, 
                     [instance.testmethod1, ...]), ...]
        """ 
        clsname = cls.__name__
        instance = cls() 
        #print "checking", instance 
        methods = []
        for methodname in dir(cls): 
            if methodname.startswith('test'): 
                name = clsname + '.' + methodname 
                methods.append((name, getattr(instance, methodname)))
        return instance.setUp, instance.tearDown, methods 
''') 

list_testmethods = app.interphook('list_testmethods')

class OutputTestModule(py.test.Item): 
    def run(self, driver): 
        outputpath = self.fspath.dirpath('output', self.fspath.purebasename) 
        assert outputpath.check(), "expected outputfile at %s" %(outputpath,)
        space = getmyspace() 
        try: 
            oldsysout = sys.stdout 
            sys.stdout = capturesysout = py.std.cStringIO.StringIO() 
            try: 
                print self.fspath.purebasename 
                run_file(str(self.fspath), space=space) 
            finally: 
                sys.stdout = oldsysout 
        except OperationError, e: 
            raise self.Failed(
                excinfo=pytestsupport.AppExceptionInfo(space, e))
        else: 
            # we want to compare outputs 
            result = capturesysout.getvalue() 
            expected = outputpath.read(mode='r') 
            if result != expected: 
                reportdiff(expected, result) 
                assert 0, "expected and real output of running test differ" 

class UnknownTestModule(py.test.collect.Module): 
    def run(self): 
        py.test.skip("missing test type for: %s" %(self.fspath.basename))
       
class UTModuleMainTest(py.test.collect.Module): 
    def _prepare(self): 
        if hasattr(self, 'space'): 
            return
        self.space = space = getmyspace() 
        def f(): 
            w_mod = make_module(space, 'unittest', mydir.join('pypy_unittest.py')) 
            self.w_TestCase = space.getattr(w_mod, space.wrap('TestCase'))
            self._testcases = self.get_testcases() 
        callex(space, f) 
       
    def run(self): 
        self._prepare() 
        return [x[0] for x in self._testcases]

    def get_testcases(self): 
        name = self.fspath.purebasename 
        space = self.space 
        w_mod = make_module(space, name, self.fspath) 

        # hack out testcases 
        space.appexec([w_mod, w_testlist], """ 
            (mod, classlist): 
                classlist[:] = []
                mod.test_main() 
            """) 
        res = []
        #print w_testlist
        for w_class in space.unpackiterable(w_testlist): 
            w_name = space.getattr(w_class, space.wrap('__name__'))
            res.append((space.str_w(w_name), w_class ))
        res.sort()
        return res 

    def join(self, name): 
        for x,w_cls in self._testcases: 
            if x == name: 
                return UTAppTestCase(name, parent=self, w_cls=w_cls) 


class UTAppTestCase(py.test.collect.Class): 
    def __init__(self, name, parent, w_cls): 
        super(UTAppTestCase, self).__init__(name, parent) 
        self.w_cls = w_cls 

    def _prepare(self): 
        if not hasattr(self, 'space'): 
            self.space = space = self.parent.space
            w_item = list_testmethods(space, self.w_cls)
            w_setup, w_teardown, w_methods = space.unpackiterable(w_item) 
            methoditems_w = space.unpackiterable(w_methods)
            self.methods_w = methods_w = []
            for w_methoditem in methoditems_w: 
                w_name, w_method = space.unpacktuple(w_methoditem) 
                name = space.str_w(w_name) 
                methods_w.append((name, w_method, w_setup, w_teardown))
            methods_w.sort() 
            
    def run(self): 
        callex(self.parent.space, self._prepare,) 
        return [x[0] for x in self.methods_w]

    def join(self, name): 
        for x in self.methods_w: 
            if x[0] == name: 
                args = x[1:]
                return AppTestCaseMethod(name, self, *args) 

class AppTestCaseMethod(py.test.Item): 
    def __init__(self, name, parent, w_method, w_setup, w_teardown): 
        super(AppTestCaseMethod, self).__init__(name, parent) 
        self.space = parent.space 
        self.w_method = w_method 
        self.w_setup = w_setup 
        self.w_teardown = w_teardown 

    def run(self, driver):      
        py.test.skip("not yet")
        space = self.space
        try:
            filename = str(self.modulepath)
            w_argv = space.sys.get('argv')
            space.setitem(w_argv, space.newslice(None, None, None),
                          space.newlist([space.wrap(filename)]))
            space.call_function(self.w_setup) 
            try: 
                try: 
                    self.execute() 
                except OperationError, e:
                    if e.match(space, space.w_KeyboardInterrupt):
                        raise KeyboardInterrupt
                    raise  
            finally: 
                self.space.call_function(self.w_teardown) 
        except OperationError, e: 
            ilevel_excinfo = py.code.ExceptionInfo() 
            excinfo=pytestsupport.AppExceptionInfo(self.space, e) 
            if excinfo.traceback: 
                raise self.Failed(excinfo=excinfo) 
            raise self.Failed(excinfo=ilevel_excinfo) 

    def execute(self): 
        self.space.call_function(self.w_method)

testmap = {
    'test_urllibnet.py'      : (False, UTModuleMainTest),
    'test_email_codecs.py'   : (False, UnknownTestModule),
    'test_linuxaudiodev.py'  : (False, OutputTestModule),
    'test_parser.py'         : (True,  UTModuleMainTest),
    'test_dummy_threading.py': (False, UTModuleMainTest),
    'test_xpickle.py'        : (False, UTModuleMainTest),
    'test_random.py'         : (False, UTModuleMainTest),
    'test_ucn.py'            : (False, UTModuleMainTest),
    'test_cookie.py'         : (False, OutputTestModule),
    'test_xreadline.py'      : (False, OutputTestModule),
    'test_thread.py'         : (False, OutputTestModule),
    'test_sys.py'            : (True,  UTModuleMainTest),
    'test_tokenize.py'       : (False, OutputTestModule),
    'test_xmllib.py'         : (False, UTModuleMainTest),
    'test___future__.py'     : (False, UnknownTestModule),
    'test_tempfile.py'       : (False, UTModuleMainTest),
    'test_bisect.py'         : (True,  UTModuleMainTest),
    'test_tarfile.py'        : (False, UTModuleMainTest),
    'test_strftime.py'       : (False, UnknownTestModule),
    'test_resource.py'       : (False, OutputTestModule),
    'test_pickletools.py'    : (False, UnknownTestModule),
    'test_inspect.py'        : (False, UnknownTestModule),
    'test_gdbm.py'           : (False, UnknownTestModule),
    'test_regex.py'          : (False, OutputTestModule),
    'test_multifile.py'      : (False, UTModuleMainTest),
    'test_dis.py'            : (True,  UTModuleMainTest),
    'test_pty.py'            : (False, OutputTestModule),
    'test_strop.py'          : (False, UTModuleMainTest),
    'test_future3.py'        : (False, UTModuleMainTest),
    'test_glob.py'           : (False, UTModuleMainTest),
    'test_binascii.py'       : (False, UTModuleMainTest),
    'test_codecs.py'         : (False, UTModuleMainTest),
    'test_socketserver.py'   : (False, UTModuleMainTest),
    'test_zipimport.py'      : (False, UTModuleMainTest),
    'test_pwd.py'            : (False, UTModuleMainTest),
    'test_popen2.py'         : (False, OutputTestModule),
    'test_future1.py'        : (False, UnknownTestModule),
    'test_funcattrs.py'      : (False, UnknownTestModule),
    'test_codeccallbacks.py' : (False, UTModuleMainTest),
    'test_whichdb.py'        : (False, UTModuleMainTest),
    'test_grammar.py'        : (False, OutputTestModule),
    'test_htmlparser.py'     : (True,  UTModuleMainTest),
    'test_getopt.py'         : (False, UnknownTestModule),
    'test_dbm.py'            : (False, UnknownTestModule),
    'test_global.py'         : (False, OutputTestModule),
    'test_calendar.py'       : (False, UTModuleMainTest),
    'test_sha.py'            : (False, UTModuleMainTest),
    'test_curses.py'         : (False, UnknownTestModule),
    'test_cmath.py'          : (True,  UnknownTestModule),
    'test_pkg.py'            : (False, OutputTestModule),
    'test_binop.py'          : (True,  UTModuleMainTest),
    'test_optparse.py'       : (False, UTModuleMainTest),
    'test_threading.py'      : (False, UnknownTestModule),
    'test_unicodedata.py'    : (False, UTModuleMainTest),
    'test_xmlrpc.py'         : (False, UTModuleMainTest),
    'test_dummy_thread.py'   : (False, UTModuleMainTest),
    'test_unicode.py'        : (False, UTModuleMainTest),
    'test_class.py'          : (False, OutputTestModule),
    'test_anydbm.py'         : (False, UTModuleMainTest),
    'test_itertools.py'      : (False, UTModuleMainTest),
    'test_stringprep.py'     : (False, UnknownTestModule),
    'test_frozen.py'         : (False, OutputTestModule),
    'test_httplib.py'        : (False, OutputTestModule),
    'test_imageop.py'        : (False, UnknownTestModule),
    'test_audioop.py'        : (False, UnknownTestModule),
    'test_zlib.py'           : (False, UTModuleMainTest),
    'test_ntpath.py'         : (False, UnknownTestModule),
    'test_heapq.py'          : (True,  UTModuleMainTest),
    'test_posix.py'          : (False, UTModuleMainTest),
    'test_mhlib.py'          : (False, UTModuleMainTest),
    'test_operations.py'     : (False, OutputTestModule),
    'test_profilehooks.py'   : (True,  UTModuleMainTest),
    'test_pkgimport.py'      : (False, UTModuleMainTest),
    'test_complex.py'        : (False, UTModuleMainTest),
    'test_builtin.py'        : (True,  UTModuleMainTest),
    'test_posixpath.py'      : (False, UTModuleMainTest),
    'test_mimetypes.py'      : (False, UTModuleMainTest),
    'test_sundry.py'         : (False, UnknownTestModule),
    'test_cl.py'             : (False, UnknownTestModule),
    'test_exceptions.py'     : (False, OutputTestModule),
    'test_compare.py'        : (True,  OutputTestModule),
    'test_socket.py'         : (False, UTModuleMainTest),
    'test_dircache.py'       : (False, UTModuleMainTest),
    'test_pyclbr.py'         : (False, UTModuleMainTest),
    'test_coercion.py'       : (False, OutputTestModule),
    'test_trace.py'          : (True,  UTModuleMainTest),
    'test_logging.py'        : (False, UTModuleMainTest),
    'test_extcall.py'        : (False, OutputTestModule),
    'test_userlist.py'       : (False, UTModuleMainTest),
    'test_longexp.py'        : (False, OutputTestModule),
    'test_cgi.py'            : (False, OutputTestModule),
    'test_wave.py'           : (False, UnknownTestModule),
    'test_normalization.py'  : (False, UTModuleMainTest),
    'test_mpz.py'            : (False, UnknownTestModule),
    'test_dumbdbm.py'        : (False, UTModuleMainTest),
    'test_gl.py'             : (False, UnknownTestModule),
    'test_capi.py'           : (False, UnknownTestModule),
    'test_strptime.py'       : (False, UTModuleMainTest),
    'test_md5.py'            : (False, OutputTestModule),
    'test_pow.py'            : (False, UTModuleMainTest),
    'test_rgbimg.py'         : (False, OutputTestModule),
    'test_dl.py'             : (False, UnknownTestModule),
    'test_slice.py'          : (False, UnknownTestModule),
    'test_pep247.py'         : (False, UnknownTestModule),
    'test_scope.py'          : (False, OutputTestModule),
    'test_fcntl.py'          : (False, UnknownTestModule),
    'test_ioctl.py'          : (False, UTModuleMainTest),
    'test_doctest.py'        : (False, UnknownTestModule),
    'test_asynchat.py'       : (False, OutputTestModule),
    'test_scriptpackages.py' : (False, UTModuleMainTest),
    'test_unary.py'          : (False, UTModuleMainTest),
    'test_poll.py'           : (False, OutputTestModule),
    'test_opcodes.py'        : (False, OutputTestModule),
    'test_gzip.py'           : (False, UnknownTestModule),
    'test_fileinput.py'      : (False, UnknownTestModule),
    'test_macfs.py'          : (False, UTModuleMainTest),
    'test_ossaudiodev.py'    : (False, OutputTestModule),
    'test_array.py'          : (False, UTModuleMainTest),
    'test_binhex.py'         : (False, UTModuleMainTest),
    'test_bastion.py'        : (False, UnknownTestModule),
    'test_descrtut.py'       : (False, UTModuleMainTest),
    'test_bz2.py'            : (False, UTModuleMainTest),
    'test_pep263.py'         : (False, UnknownTestModule),
    'test_bsddb3.py'         : (False, UTModuleMainTest),
    'test_MimeWriter.py'     : (False, OutputTestModule),
    'test_urllib.py'         : (False, UTModuleMainTest),
    'test_cpickle.py'        : (False, UTModuleMainTest),
    'test_urlparse.py'       : (True,  UTModuleMainTest),
    'test_mmap.py'           : (False, OutputTestModule),
    'test_symtable.py'       : (False, UnknownTestModule),
    'test_traceback.py'      : (False, UTModuleMainTest),
    'test_quopri.py'         : (False, UTModuleMainTest),
    'test_contains.py'       : (False, UnknownTestModule),
    'test_pickle.py'         : (False, UTModuleMainTest),
    'test___all__.py'        : (False, UTModuleMainTest),
    'test_re.py'             : (False, UTModuleMainTest),
    'test_compile.py'        : (True,  UTModuleMainTest),
    'test_augassign.py'      : (False, OutputTestModule),
    'test_largefile.py'      : (False, UnknownTestModule),
    'test_mailbox.py'        : (False, UTModuleMainTest),
    'test_unicode_file.py'   : (False, OutputTestModule),
    'test_plistlib.py'       : (False, UTModuleMainTest),
    'test_mimetools.py'      : (False, UTModuleMainTest),
    'test_shelve.py'         : (False, UTModuleMainTest),
    'test_rfc822.py'         : (False, UTModuleMainTest),
    'test_pprint.py'         : (True,  UTModuleMainTest),
    'test_rotor.py'          : (False, OutputTestModule),
    'test_getargs.py'        : (False, UnknownTestModule),
    'test_mutants.py'        : (False, UnknownTestModule),
    'test_doctest2.py'       : (False, UTModuleMainTest),
    'test_softspace.py'      : (False, UnknownTestModule),
    'test_copy_reg.py'       : (False, UTModuleMainTest),
    'test_cd.py'             : (False, UnknownTestModule),
    'test_struct.py'         : (False, UnknownTestModule),
    'test_sort.py'           : (False, UnknownTestModule),
    'test_imgfile.py'        : (False, UnknownTestModule),
    'test_descr.py'          : (False, UTModuleMainTest),
    'test_long_future.py'    : (False, UnknownTestModule),
    'test_file.py'           : (False, UnknownTestModule),
    'test_richcmp.py'        : (False, UTModuleMainTest),
    'test_call.py'           : (True,  UTModuleMainTest),
    'test_nis.py'            : (False, OutputTestModule),
    'test_timeout.py'        : (False, UTModuleMainTest),
    'test_support.py'        : (False, UnknownTestModule),
    'test_csv.py'            : (False, UTModuleMainTest),
    'test_future2.py'        : (False, UnknownTestModule),
    'test_aepack.py'         : (False, UTModuleMainTest),
    'test_pyexpat.py'        : (False, OutputTestModule),
    'test_import.py'         : (False, UnknownTestModule),
    'test_openpty.py'        : (False, OutputTestModule),
    'test_structseq.py'      : (False, UnknownTestModule),
    'test_os.py'             : (False, UTModuleMainTest),
    'test_repr.py'           : (False, UTModuleMainTest),
    'test_generators.py'     : (False, UTModuleMainTest),
    'test_future.py'         : (False, OutputTestModule),
    'test_atexit.py'         : (False, UnknownTestModule),
    'test_zipfile.py'        : (False, UnknownTestModule),
    'test_urllib2.py'        : (False, UnknownTestModule),
    'test_minidom.py'        : (False, UnknownTestModule),
    'test_winreg.py'         : (False, OutputTestModule),
    'test_iter.py'           : (False, UTModuleMainTest),
    'test_fnmatch.py'        : (False, UTModuleMainTest),
    'test_datetime.py'       : (True,  UTModuleMainTest),
    'test_string.py'         : (True,  UTModuleMainTest),
    'test_sets.py'           : (False, UTModuleMainTest),
    'test_textwrap.py'       : (True,  UTModuleMainTest),
    'test_select.py'         : (False, UnknownTestModule),
    'test_filecmp.py'        : (False, UTModuleMainTest),
    'test_base64.py'         : (True,  UTModuleMainTest),
    'test_long.py'           : (False, UnknownTestModule),
    'test_hexoct.py'         : (True,  UTModuleMainTest),
    'test_threaded_import.py': (False, UTModuleMainTest),
    'test_uu.py'             : (False, UTModuleMainTest),
    'test_gc.py'             : (False, UnknownTestModule),
    'test_StringIO.py'       : (False, UTModuleMainTest),
    'test_module.py'         : (False, UnknownTestModule),
    'test_profile.py'        : (False, UTModuleMainTest),
    'test_winsound.py'       : (False, UTModuleMainTest),
    'test_signal.py'         : (False, OutputTestModule),
    'test_popen.py'          : (False, OutputTestModule),
    'test_hotshot.py'        : (False, UTModuleMainTest),
    'test_marshal.py'        : (False, UnknownTestModule),
    'test_time.py'           : (False, UTModuleMainTest),
    'test_sunaudiodev.py'    : (False, UnknownTestModule),
    'test_operator.py'       : (True,  UTModuleMainTest),
    'test_univnewlines.py'   : (False, UTModuleMainTest),
    'test_codeop.py'         : (True,  UTModuleMainTest),
    'test_sax.py'            : (False, UnknownTestModule),
    'test_email.py'          : (False, UTModuleMainTest),
    'test_timing.py'         : (False, UnknownTestModule),
    'test_macpath.py'        : (False, UTModuleMainTest),
    'test_hmac.py'           : (False, UTModuleMainTest),
    'test_new.py'            : (False, OutputTestModule),
    'test_imp.py'            : (False, UTModuleMainTest),
    'test_gettext.py'        : (False, UTModuleMainTest),
    'test_fork1.py'          : (False, UnknownTestModule),
    'test_str.py'            : (False, UTModuleMainTest),
    'test_netrc.py'          : (False, UTModuleMainTest),
    'test_importhooks.py'    : (False, UTModuleMainTest),
    'test_bufio.py'          : (False, UnknownTestModule),
    'test_syntax.py'         : (False, UTModuleMainTest),
    'test_grp.py'            : (False, UTModuleMainTest),
    'test_imaplib.py'        : (False, UnknownTestModule),
    'test_charmapcodec.py'   : (False, UTModuleMainTest),
    'test_userdict.py'       : (False, UTModuleMainTest),
    'test_robotparser.py'    : (False, UTModuleMainTest),
    'test_commands.py'       : (True,  UTModuleMainTest),
    'test_eof.py'            : (False, UTModuleMainTest),
    'test_weakref.py'        : (False, UTModuleMainTest),
    'test_fpformat.py'       : (False, UTModuleMainTest),
    'test_locale.py'         : (False, UnknownTestModule),
    'test_htmllib.py'        : (True,  UTModuleMainTest),
    'test_types.py'          : (False, OutputTestModule),
    'test_bsddb185.py'       : (False, UTModuleMainTest),
    'test_math.py'           : (False, OutputTestModule),
    'test_hash.py'           : (True,  UTModuleMainTest),
    'test_al.py'             : (False, UnknownTestModule),
    'test_errno.py'          : (False, UnknownTestModule),
    'test_queue.py'          : (False, UnknownTestModule),
    'test_shutil.py'         : (False, UTModuleMainTest),
    'test_bsddb.py'          : (False, UTModuleMainTest),
    'test_sgmllib.py'        : (True,  UTModuleMainTest),
    'test_pep277.py'         : (False, UTModuleMainTest),
    'test_macostools.py'     : (False, UTModuleMainTest),
    'test_warnings.py'       : (False, UTModuleMainTest),
    'test_copy.py'           : (False, UTModuleMainTest),
    'test_getargs2.py'       : (False, UTModuleMainTest),
    'test_bool.py'           : (False, UTModuleMainTest),
    'test_unpack.py'         : (False, UnknownTestModule),
    'test_enumerate.py'      : (False, UTModuleMainTest),
    'test_socket_ssl.py'     : (False, UTModuleMainTest),
    'test_userstring.py'     : (False, UTModuleMainTest),
    'test_threadedtempfile.py': (False, UTModuleMainTest),
    'test_shlex.py'          : (False, UTModuleMainTest),
    'test_crypt.py'          : (False, UnknownTestModule),
    'test_format.py'         : (False, UnknownTestModule),
    'test_isinstance.py'     : (True,  UTModuleMainTest),
    'test_cfgparser.py'      : (False, UTModuleMainTest),
    'test_difflib.py'        : (False, UnknownTestModule),
}
