/************************************************************/
/** C header subsection: debugging raw malloc bound checks **/


#ifdef RPY_LL_ASSERT

void RPyRawMalloc_Record_Size(void *, Signed);
void RPyRawMalloc_Forget_Size(void *);
Signed RPyRawMalloc_Size(void *);

#else

#define RPyRawMalloc_Record_Size(ptr, size)

#endif
