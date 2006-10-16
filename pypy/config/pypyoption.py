import autopath
import py
from pypy.config.config import OptionDescription, BoolOption, IntOption
from pypy.config.config import ChoiceOption, StrOption, to_optparse, Config

modulepath = py.magic.autopath().dirpath().dirpath().join("module")
all_modules = [p.basename for p in modulepath.listdir()
                   if p.check(dir=True, dotfile=False)]

default_modules = dict.fromkeys(
    [#"unicodedata",
     "_codecs", "gc", "_weakref", "array", "marshal", "errno",
     "math", "_sre", "_pickle_support", "sys", "exceptions", "__builtins__",
     "recparser", "symbol", "_random"])
                              
pypy_optiondescription = OptionDescription("pypy", "All PyPy Options", [
    OptionDescription("objspace", "Object Space Option", [
        ChoiceOption("name", "Object Space name",
                     ["std", "flow", "logic", "thunk", "cpy"], "std",
                     requires = {
                         "thunk": [("objspace.geninterp", False)],
                         "logic": [("objspace.geninterp", False)],
                     },
                     cmdline='--objspace -o'),

        ChoiceOption("parser", "parser",
                     ["pypy", "cpython"], "pypy",
                     cmdline='--parser'),

        ChoiceOption("compiler", "compiler",
                     ["cpython", "ast"], "ast",
                     cmdline='--compiler'),

        BoolOption("nofaking", "disallow faking in the object space",
                   default=False,
                   requires=[
                       ("objspace.uselibfile", True),
                       ("objspace.usemodules.posix", True),
                       ("objspace.usemodules.time", True),
                       ("objspace.usemodules.errno", True)],
                   cmdline='--nofaking'),

        BoolOption("uselibfile", "use the applevel file implementation",
                   default=False,
                   cmdline='--uselibfile'),

        OptionDescription("usemodules", "Which Modules should be used", [
            BoolOption(modname, "use module %s" % (modname, ),
                       default=modname in default_modules,
                       cmdline="--withmod-%s" % (modname, ))
            for modname in all_modules]),

        BoolOption("geninterp", "specify whether geninterp should be used"),

        BoolOption("logbytecodes",
                   "keep track of bytecode usage",
                   default=False),
       
        OptionDescription("std", "Standard Object Space Options", [
            BoolOption("withsmallint", "use tagged integers",
                       default=False),

            BoolOption("withprebuiltint", "prebuilt commonly used int objects",
                       default=False,
                       requires=[("objspace.std.withsmallint", False)]),

            IntOption("prebuiltintfrom", "lowest integer which is prebuilt",
                      default=-5, cmdline="--prebuiltinfrom"),

            IntOption("prebuiltintto", "highest integer which is prebuilt",
                      default=100, cmdline="--prebuiltintto"),

            BoolOption("withstrjoin", "use strings optimized for addition",
                       default=False),

            BoolOption("withstrslice", "use strings optimized for slicing",
                       default=False),

            BoolOption("withstrdict",
                       "use dictionaries optimized for string keys",
                       default=False),

            BoolOption("withmultidict",
                       "use dictionaries optimized for flexibility",
                       default=False,
                       requires=[("objspace.std.withstrdict", False)]),

            BoolOption("withdictmeasurement",
                       "create huge files with masses of information "
                       "about dictionaries",
                       default=False,
                       requires=[("objspace.std.withmultidict", True)]),

            BoolOption("oldstyle",
                       "specify whether the default metaclass should be classobj",
                       default=False, cmdline="--oldstyle"),
         ]),


    ]),

    BoolOption("translating", "indicates whether we are translating currently",
               default=False, cmdline=None),

    OptionDescription("translation", "Translation Options", [
        BoolOption("stackless", "compile stackless features in",
                   default=False, cmdline="--stackless",
                   requires=[("translation.type_system", "lltype"),
                             ("objspace.usemodules._stackless", True)]),
        ChoiceOption("type_system", "Type system to use when RTyping",
                     ["lltype", "ootype"], cmdline=None),
        ChoiceOption("backend", "Backend to use for code generation",
                     ["c", "llvm", "cli", "js", "squeak", "cl"],
                     requires={
                         "c":      [("translation.type_system", "lltype")],
                         "llvm":   [("translation.type_system", "lltype")],
                         "cli":    [("translation.type_system", "ootype")],
                         "js":     [("translation.type_system", "ootype")],
                         "squeak": [("translation.type_system", "ootype")],
                         "cl":     [("translation.type_system", "ootype")],
                         }),
        ChoiceOption("gc", "Garbage Collection Strategy",
                     ["boehm", "ref", "framework", "none", "stacklessgc",
                      "exact_boehm"],
                      "boehm", requires={
                         "stacklessgc": [("translation.stackless", True)]},
                      cmdline="--gc"),

        BoolOption("thread", "enable use of threading primitives",
                   default=False),
        BoolOption("verbose", "Print extra information", default=False),
        BoolOption("debug", "Record extra annotation information",
                   cmdline="-d --debug", default=False),
        BoolOption("insist", "Try hard to go on RTyping", default=False,
                   cmdline="--insist"),
        BoolOption("countmallocs", "Count mallocs and frees", default=False,
                   cmdline=None),
        BoolOption("lowmem", "Try to use little memory during translation",
                   default=False, cmdline="--lowmem",
                   requires=[("objspace.geninterp", False)]),

        # misc
        StrOption("cc", "Specify compiler", default='', cmdline="--cc"),
        StrOption("profopt", "Specify profile based optimization script",
                  default="", cmdline="--profopt"),
        BoolOption("batch", "Don't run interactive helpers", default=False,
                   cmdline="--batch", negation=False),
        IntOption("huge", "Threshold in the number of functions after which"
                          "a local call graph and not a full one is displayed",
                  default=100, cmdline="--huge"),
        BoolOption("text", "Don't start the pygame viewer", default=False,
                   cmdline="--text", negation=False),
        BoolOption("debug_transform", "Perform the debug transformation",
                   default=False, cmdline=None, negation=False),

        # Flags of the TranslationContext:
        BoolOption("simplifying", "Simplify flow graphs", default=True),
        BoolOption("do_imports_immediately", "XXX", default=True,
                   cmdline=None),
        BoolOption("builtins_can_raise_exceptions", "XXX", default=False,
                   cmdline=None),
        BoolOption("list_comprehension_operations", "XXX", default=False,
                   cmdline=None),

        OptionDescription("backendopt", "Backend Optimization Options", [
            BoolOption("print_statistics", "Print statistics while optimizing",
                       default=False),
            BoolOption("merge_if_blocks", "Merge if ... elif chains",
                       cmdline="--if-block-merge", default=True),
            BoolOption("raisingop2direct_call",
                       "Transform exception raising operations",
                       default=False, cmdline="--raisingop2direct_call"),
            BoolOption("mallocs", "Remove mallocs", default=True),
            BoolOption("propagate", "Constant propagation, deprecated",
                       default=False),
            BoolOption("constfold", "Constant propagation",
                       default=True),
            BoolOption("heap2stack", "Escape analysis and stack allocation",
                       default=False,
                       requires=[("translation.stackless", False)]),
            BoolOption("clever_malloc_removal",
                       "Remove mallocs in a clever way", default=False),
            IntOption("inline_threshold", "Threshold when to inline functions",
                      default=1, cmdline=None),
        ]),
        OptionDescription("goals",
                          "Goals that should be reached during translation", [
            BoolOption("annotate", "Do type inference", default=False,
                       cmdline="-a --annotate", negation=False),
            BoolOption("no_annotate", "Don't do type inference", default=False,
                       cmdline="--no-annotate", negation=False),
            BoolOption("rtype", "Do rtyping", default=False,
                       cmdline="-t --rtype", negation=False),
            BoolOption("no_rtype", "Don't do rtyping", default=False,
                       cmdline="--no-rtype", negation=False),
            BoolOption("backendopt", "Do backend optimizations", default=False,
                       cmdline="--backendopt", negation=False),
            BoolOption("no_backenopt", "Don't do backend optimizations",
                       default=False, cmdline="--no-backendopt", negation=False),
            BoolOption("source", "Create source", default=False,
                       cmdline="-s --source", negation=False),
            BoolOption("no_source", "Don't create source", default=False,
                       cmdline="--no-source", negation=False),
            BoolOption("compile", "Compile", default=False,
                       cmdline="--compile", negation=False),
            BoolOption("no_compile", "Don't compile", default=False,
                       cmdline="--no-compile", negation=False),
            BoolOption("llinterpret", "Interpret the rtyped flow graphs",
                       default=False, cmdline="--llinterpret", negation=False),
            ChoiceOption("fork_before",
                         "(UNIX) Create restartable checkpoint before step",
                         ["annotate", "rtype", "backendopt", "database",
                          "source"], default=None, cmdline="--fork-before"),

        ]),
    ]),
])


if __name__ == '__main__':
    config = Config(pypy_optiondescription)
    print config.getpaths()
    parser = to_optparse(config) #, useoptions=["translation.*"])
    option, args = parser.parse_args()
    print config
