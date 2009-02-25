import py

Option = py.test.config.Option
option = py.test.config.addoptions("smalltalk options",
        Option('--bc-trace',
               action="store_true",
               dest="bc_trace",
               default=False,
               help="print bytecodes and stack during execution"),
        Option('--prim-trace',
               action="store_true",
               dest="prim_trace",
               default=False,
               help="print called primitives during execution"),
)
