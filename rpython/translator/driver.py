import sys, os
import os.path
import shutil

from rpython.translator.translator import TranslationContext
from rpython.translator.goal import query
from rpython.translator.goal.timing import Timer
from rpython.annotator.listdef import s_list_of_strings
from rpython.annotator import policy as annpolicy
from rpython.tool.udir import udir
from rpython.rlib.debug import debug_start, debug_print, debug_stop
from rpython.rlib.entrypoint import secondary_entrypoints,\
     annotated_jit_entrypoints

import py
from rpython.tool.ansi_print import AnsiLogger

log = AnsiLogger("translation")

# TODO:
# sanity-checks using states

# set of translation steps to profile
PROFILE = set([])

class Instrument(Exception):
    pass


class ProfInstrument(object):
    name = "profinstrument"
    def __init__(self, datafile, compiler):
        self.datafile = datafile
        self.compiler = compiler

    def first(self):
        return self.compiler._build()

    def probe(self, exe, args):
        env = os.environ.copy()
        env['PYPY_INSTRUMENT_COUNTERS'] = str(self.datafile)
        self.compiler.platform.execute(exe, args, env=env)

    def after(self):
        # xxx
        os._exit(0)


class TranslationDriver(object):
    _backend_extra_options = {}

    def __init__(self, setopts=None, default_goal=None, disable=(),
                 exe_name=None, config=None, overrides=None):
        from rpython.config import translationoption
        self.timer = Timer()

        self.log = log

        if config is None:
            config = translationoption.get_combined_translation_config(translating=True)
        # XXX patch global variable with translation config
        translationoption._GLOBAL_TRANSLATIONCONFIG = config
        self.config = config
        if overrides is not None:
            self.config.override(overrides)

        if setopts is not None:
            self.config.set(**setopts)

        self.exe_name = exe_name

        self.done = set()

        self.disable(disable)

        if default_goal:
            default_goal, = self.backend_select_goals([default_goal])
            if default_goal in self.backend_select_goals(self._disabled):
                default_goal = None

        self.default_goal = default_goal
        self.extra_goals = []

    def annotate(self):
        return self.run_task(self.task_annotate, 'annotate')

    def rtype_lltype(self):
        self.annotate()
        return self.run_task(self.task_rtype_lltype, 'rtype_lltype')

    def pyjitpl_lltype(self):
        self.rtype_lltype()
        return self.run_task(self.task_pyjitpl_lltype, 'pyjitpl_lltype')

    def jittest_lltype(self):
        self.rtype_lltype()
        return self.run_task(self.task_jittest_lltype, 'jittest_lltype')

    def backendopt_lltype(self):
        self.rtype_lltype()
        if 'pyjitpl_lltype' in self.extra_goals:
            self.pyjitpl_lltype()
        if 'jittest_lltype' in self.extra_goals:
            self.jittest_lltype()
        
        return self.run_task(self.task_backendopt_lltype,
                             'backendopt_lltype')

    def stackcheckinsertion_lltype(self):
        self.rtype_lltype()
        disabled = self.backend_select_goals(self._disabled)
        if 'backendopt_lltype' not in disabled:
            self.backendopt_lltype()
        return self.run_task(self.task_stackcheckinsertion_lltype,
                             'stackcheckinsertion_lltype')

    def llinterpret_lltype(self):
        self.stackcheckinsertion_lltype()
        return self.run_task(self.task_llinterpret_lltype,
                             'llinterpret_lltype')

    def source_c(self):
        if 'check_for_boehm' not in self.done:
            self.possibly_check_for_boehm()
            self.done.add('check_for_boehm')
        self.stackcheckinsertion_lltype()
        self.run_task(self.task_database_c, 'database_c')
        return self.run_task(self.task_source_c, 'source_c')

    def compile_c(self):
        self.source_c()
        return self.run_task(self.task_compile_c, 'compile_c')

    def run_c(self):
        self.compile_c()
        return self.run_task(self.task_run_c, 'run_c')

    def set_extra_goals(self, goals):
        self.extra_goals = self.backend_select_goals(goals)

    def set_backend_extra_options(self, extra_options):
        self._backend_extra_options = extra_options

    def get_info(self): # XXX more?
        d = {'backend': self.config.translation.backend}
        return d

    def get_backend_and_type_system(self):
        type_system = self.config.translation.type_system
        backend = self.config.translation.backend
        return backend, type_system

    def backend_select_goals(self, goals):
        backend, ts = self.get_backend_and_type_system()
        result = []
        for goal in goals:
            names = ['task_%s_%s' % (goal, backend),
                     'task_%s_%s' % (goal, ts),
                     'task_%s' % (goal,)]
            if set(names).intersection(self.done):
                continue
            for name in names:
                task = getattr(self, name, None)
                if task is not None:
                    result.append(name[len('task_'):])
                    break
            else:
                raise Exception("cannot infer complete goal from: %r" % goal)
        return result
            
    def disable(self, to_disable):
        self._disabled = to_disable

    def run_task(self, task, name, *args, **kwargs):
        if name in self.done or name in self._disabled:
            return
        task = getattr(self, 'task_%s' % name)

        self.fork_before(name)

        debug_start('translation-task')
        debug_print('starting', name)
        self.timer.start_event(name)
        try:
            instrument = False
            try:
                if name in PROFILE:
                    res = self._profile(name, func)
                else:
                    res = task(*args, **kwargs)
            except Instrument:
                instrument = True
            if instrument:
                self.proceed(['compile_c'])
                assert False, 'we should not get here'
        finally:
            try:
                debug_stop('translation-task')
                self.timer.end_event(name)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                pass
        #import gc; gc.dump_rpy_heap('rpyheap-after-%s.dump' % goal)

        self.log.info('usession directory: %s' % (udir,))

        self.done.add(name)
        return res

    def proceed(self, goals):
        if not goals:
            goals = [self.default_goal]
        backend, ts = self.get_backend_and_type_system()
        goals = set(self.backend_select_goals(goals + self.extra_goals))
        if not goals:
            self.log.info('Nothing to do.')
        self.extra_goals += goals

        # run C goals first to catch missing boehm.
        for goal in goals:
            if goal.endswith('_c'):
                getattr(self, goal)()
        for goal in goals:
            getattr(self, goal)()

    def setup(self, entry_point, inputtypes, policy=None, extra={}, empty_translator=None):
        standalone = inputtypes is None
        self.standalone = standalone

        if standalone:
            # the 'argv' parameter
            inputtypes = [s_list_of_strings]
        self.inputtypes = inputtypes

        if policy is None:
            policy = annpolicy.AnnotatorPolicy()
        self.policy = policy

        self.extra = extra

        if empty_translator:
            translator = empty_translator
        else:
            translator = TranslationContext(config=self.config)

        self.entry_point = entry_point
        self.translator = translator
        self.libdef = None
        self.secondary_entrypoints = []

        if self.config.translation.secondaryentrypoints:
            for key in self.config.translation.secondaryentrypoints.split(","):
                try:
                    points = secondary_entrypoints[key]
                except KeyError:
                    raise KeyError("Entrypoint %r not found (not in %r)" %
                                   (key, secondary_entrypoints.keys()))
                self.secondary_entrypoints.extend(points)

        self.translator.driver_instrument_result = self.instrument_result

    def setup_library(self, libdef, policy=None, extra={}, empty_translator=None):
        """ Used by carbon python only. """
        self.setup(None, None, policy, extra, empty_translator)
        self.libdef = libdef
        self.secondary_entrypoints = libdef.functions

    def instrument_result(self, args):
        backend, ts = self.get_backend_and_type_system()
        if backend != 'c' or sys.platform == 'win32':
            raise Exception("instrumentation requires the c backend"
                            " and unix for now")

        datafile = udir.join('_instrument_counters')
        makeProfInstrument = lambda compiler: ProfInstrument(datafile, compiler)

        pid = os.fork()
        if pid == 0:
            # child compiling and running with instrumentation
            self.config.translation.instrument = True
            self.config.translation.instrumentctl = (makeProfInstrument,
                                                     args)
            raise Instrument
        else:
            pid, status = os.waitpid(pid, 0)
            if os.WIFEXITED(status):
                status = os.WEXITSTATUS(status)
                if status != 0:
                    raise Exception("instrumentation child failed: %d" % status)
            else:
                raise Exception("instrumentation child aborted")
            import array, struct
            n = datafile.size()//struct.calcsize('L')
            datafile = datafile.open('rb')
            counters = array.array('L')
            counters.fromfile(datafile, n)
            datafile.close()
            return counters

    def info(self, msg):
        log.info(msg)

    def _profile(self, goal, func):
        from cProfile import Profile
        from rpython.tool.lsprofcalltree import KCacheGrind
        d = {'func':func}
        prof = Profile()
        prof.runctx("res = func()", globals(), d)
        KCacheGrind(prof).output(open(goal + ".out", "w"))
        return d['res']

    def task_annotate(self):
        """ Annotate
        """
        # includes annotation and annotatation simplifications
        translator = self.translator
        policy = self.policy
        self.log.info('with policy: %s.%s' % (policy.__class__.__module__, policy.__class__.__name__))

        annotator = translator.buildannotator(policy=policy)

        if self.secondary_entrypoints is not None:
            for func, inputtypes in self.secondary_entrypoints:
                if inputtypes == Ellipsis:
                    continue
                annotator.build_types(func, inputtypes, False)

        if self.entry_point:
            s = annotator.build_types(self.entry_point, self.inputtypes)
            translator.entry_point_graph = annotator.bookkeeper.getdesc(self.entry_point).getuniquegraph()
        else:
            s = None

        self.sanity_check_annotation()
        if self.entry_point and self.standalone and s.knowntype != int:
            raise Exception("stand-alone program entry point must return an "
                            "int (and not, e.g., None or always raise an "
                            "exception).")
        annotator.complete()
        annotator.simplify()
        return s


    def sanity_check_annotation(self):
        translator = self.translator
        irreg = query.qoutput(query.check_exceptblocks_qgen(translator))
        if irreg:
            self.log.info("Some exceptblocks seem insane")

        lost = query.qoutput(query.check_methods_qgen(translator))
        assert not lost, "lost methods, something gone wrong with the annotation of method defs"

    def task_rtype_lltype(self):
        """ RTyping - lltype version
        """
        rtyper = self.translator.buildrtyper()
        rtyper.specialize(dont_simplify_again=True)

    def task_pyjitpl_lltype(self):
        """ Generate bytecodes for JIT and flow the JIT helper functions
        lltype version
        """
        from rpython.jit.codewriter.policy import JitPolicy
        get_policy = self.extra.get('jitpolicy', None)
        if get_policy is None:
            self.jitpolicy = JitPolicy()
        else:
            self.jitpolicy = get_policy(self)
        #
        from rpython.jit.metainterp.warmspot import apply_jit
        apply_jit(self.translator, policy=self.jitpolicy,
                  backend_name=self.config.translation.jit_backend, inline=True)
        #
        self.log.info("the JIT compiler was generated")

    def task_jittest_lltype(self):
        """ Run with the JIT on top of the llgraph backend
        """
        # parent process loop: spawn a child, wait for the child to finish,
        # print a message, and restart
        from rpython.translator.goal import unixcheckpoint
        unixcheckpoint.restartable_point(auto='run')
        # load the module rpython/jit/tl/jittest.py, which you can hack at
        # and restart without needing to restart the whole translation process
        from rpython.jit.tl import jittest
        jittest.jittest(self)

    def task_backendopt_lltype(self):
        """ Run all backend optimizations - lltype version
        """
        from rpython.translator.backendopt.all import backend_optimizations
        backend_optimizations(self.translator, replace_we_are_jitted=True)


    def task_stackcheckinsertion_lltype(self):
        from rpython.translator.transform import insert_ll_stackcheck
        count = insert_ll_stackcheck(self.translator)
        self.log.info("inserted %d stack checks." % (count,))


    def possibly_check_for_boehm(self):
        if self.config.translation.gc == "boehm":
            from rpython.rtyper.tool.rffi_platform import configure_boehm
            from rpython.translator.platform import CompilationError
            try:
                configure_boehm(self.translator.platform)
            except CompilationError as e:
                i = 'Boehm GC not installed.  Try e.g. "translate.py --gc=minimark"'
                raise Exception(str(e) + '\n' + i)

    def task_database_c(self):
        """ Create a database for further backend generation
        """
        translator = self.translator
        if translator.annotator is not None:
            translator.frozen = True

        standalone = self.standalone
        get_gchooks = self.extra.get('get_gchooks', lambda: None)
        gchooks = get_gchooks()

        if standalone:
            from rpython.translator.c.genc import CStandaloneBuilder
            cbuilder = CStandaloneBuilder(self.translator, self.entry_point,
                                          config=self.config, gchooks=gchooks,
                      secondary_entrypoints=
                      self.secondary_entrypoints + annotated_jit_entrypoints)
        else:
            from rpython.translator.c.dlltool import CLibraryBuilder
            functions = [(self.entry_point, None)] + self.secondary_entrypoints + annotated_jit_entrypoints
            cbuilder = CLibraryBuilder(self.translator, self.entry_point,
                                       functions=functions,
                                       name='libtesting',
                                       config=self.config,
                                       gchooks=gchooks)
        database = cbuilder.build_database()
        self.log.info("database for generating C source was created")
        self.cbuilder = cbuilder
        self.database = database

    def task_source_c(self):
        """ Create C source files from the generated database
        """
        cbuilder = self.cbuilder
        database = self.database
        if self._backend_extra_options.get('c_debug_defines', False):
            defines = cbuilder.DEBUG_DEFINES
        else:
            defines = {}
        if self.exe_name is not None:
            exe_name = self.exe_name % self.get_info()
        else:
            exe_name = None
        c_source_filename = cbuilder.generate_source(database, defines,
                                                     exe_name=exe_name)
        self.log.info("written: %s" % (c_source_filename,))
        if self.config.translation.dump_static_data_info:
            from rpython.translator.tool.staticsizereport import dump_static_data_info
            targetdir = cbuilder.targetdir
            fname = dump_static_data_info(self.log, database, targetdir)
            dstname = self.compute_exe_name() + '.staticdata.info'
            shutil_copy(str(fname), str(dstname))
            self.log.info('Static data info written to %s' % dstname)

    def compute_exe_name(self, suffix=''):
        newexename = self.exe_name % self.get_info()
        if '/' not in newexename and '\\' not in newexename:
            newexename = './' + newexename
        newname = py.path.local(newexename)
        if suffix:
            newname = newname.new(purebasename = newname.purebasename + suffix)
        return newname

    def create_exe(self):
        """ Copy the compiled executable into current directory, which is
            pypy/goal on nightly builds
        """
        if self.exe_name is not None:
            exename = self.c_entryp
            newexename = mkexename(self.compute_exe_name())
            shutil_copy(str(exename), str(newexename))
            if self.cbuilder.shared_library_name is not None:
                soname = self.cbuilder.shared_library_name
                newsoname = newexename.new(basename=soname.basename)
                shutil_copy(str(soname), str(newsoname))
                self.log.info("copied: %s" % (newsoname,))
                if sys.platform == 'win32':
                    # Copy pypyw.exe
                    newexename = mkexename(self.compute_exe_name(suffix='w'))
                    exe = py.path.local(exename)
                    exename = exe.new(purebasename=exe.purebasename + 'w')
                    shutil_copy(str(exename), str(newexename))
                    # for pypy, the import library is renamed and moved to
                    # libs/python32.lib, according to the pragma in pyconfig.h
                    libname = self.config.translation.libname
                    oldlibname = soname.new(ext='lib')
                    if not libname:
                        libname = oldlibname.basename
                        libname = str(newsoname.dirpath().join(libname))
                    shutil.copyfile(str(oldlibname), libname)
                    self.log.info("copied: %s to %s" % (oldlibname, libname,))
                    # the pdb file goes in the same place as pypy(w).exe
                    ext_to_copy = ['pdb',]
                    for ext in ext_to_copy:
                        name = soname.new(ext=ext)
                        newname = newexename.new(basename=soname.basename)
                        shutil.copyfile(str(name), str(newname.new(ext=ext)))
                        self.log.info("copied: %s" % (newname,))
            self.c_entryp = newexename
        self.log.info("created: %s" % (self.c_entryp,))

    def task_compile_c(self):
        """ Compile the generated C code using either makefile or
        translator/platform
        """
        cbuilder = self.cbuilder
        kwds = {}
        if self.standalone and self.exe_name is not None:
            kwds['exe_name'] = self.compute_exe_name().basename
        cbuilder.compile(**kwds)

        if self.standalone:
            self.c_entryp = cbuilder.executable_name
            self.create_exe()
        else:
            self.c_entryp = cbuilder.get_entry_point()

    def task_llinterpret_lltype(self):
        from rpython.rtyper.llinterp import LLInterpreter

        translator = self.translator
        interp = LLInterpreter(translator.rtyper)
        bk = translator.annotator.bookkeeper
        graph = bk.getdesc(self.entry_point).getuniquegraph()
        v = interp.eval_graph(graph,
                              self.extra.get('get_llinterp_args',
                                             lambda: [])())

        log.llinterpret("result -> %s" % v)

    @classmethod
    def from_targetspec(cls, targetspec_dic, config=None, args=None,
                        empty_translator=None,
                        disable=[],
                        default_goal=None):
        if args is None:
            args = []

        driver = cls(config=config, default_goal=default_goal,
                     disable=disable)
        target = targetspec_dic['target']
        spec = target(driver, args)

        try:
            entry_point, inputtypes, policy = spec
        except TypeError:
            # not a tuple at all
            entry_point = spec
            inputtypes = policy = None
        except ValueError:
            policy = None
            entry_point, inputtypes = spec


        driver.setup(entry_point, inputtypes,
                     policy=policy,
                     extra=targetspec_dic,
                     empty_translator=empty_translator)
        return driver

    def prereq_checkpt_rtype(self):
        assert 'rpython.rtyper.rmodel' not in sys.modules, (
            "cannot fork because the rtyper has already been imported")
    prereq_checkpt_rtype_lltype = prereq_checkpt_rtype

    # checkpointing support
    def fork_before(self, goal):
        fork_before = self.config.translation.fork_before
        if fork_before:
            fork_before, = self.backend_select_goals([fork_before])
            if not fork_before in self.done and fork_before == goal:
                prereq = getattr(self, 'prereq_checkpt_%s' % goal, None)
                if prereq:
                    prereq()
                from rpython.translator.goal import unixcheckpoint
                unixcheckpoint.restartable_point(auto='run')

def mkexename(name):
    if sys.platform == 'win32':
        name = name.new(ext='exe')
    return name

if os.name == 'posix':
    def shutil_copy(src, dst):
        # this version handles the case where 'dst' is an executable
        # currently being executed
        shutil.copy(src, dst + '~')
        os.rename(dst + '~', dst)
else:
    shutil_copy = shutil.copy
