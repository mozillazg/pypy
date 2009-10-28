
#ifndef STANDALONE_ENTRY_POINT
#  define STANDALONE_ENTRY_POINT   PYPY_STANDALONE
#endif

char *RPython_StartupCode(void);  /* forward */


/* prototypes */

int main(int argc, char *argv[]);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

int main(int argc, char *argv[])
{
    char *errmsg;
    int i, exitcode;
    RPyListOfString *list;

    instrument_setup();

    errmsg = RPython_StartupCode();
    if (errmsg) goto error;

    exitcode = STANDALONE_ENTRY_POINT(argc, argv);
    if (RPyExceptionOccurred()) {
        /* fish for the exception type, at least */
#ifndef AVR
        fprintf(stderr, "Fatal RPython error: %s\n",
                RPyFetchExceptionType()->ov_name->items);
#endif
        abort();
    }
    return exitcode;

 error:
#ifndef AVR
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
#endif
    abort();
}

#endif /* PYPY_NOT_MAIN_FILE */
