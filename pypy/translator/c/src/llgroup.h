

#define GROUP_MEMBER_OFFSET(group, membername)  \
  ((unsigned short)((((char*)&membername) - ((char*)&group)) / sizeof(long)))

#define OP_GET_GROUP_MEMBER(groupptr, compactoffset, r)  \
  r = ((char*)groupptr) + ((long)compactoffset)*sizeof(long)

#define OP_GET_NEXT_GROUP_MEMBER(groupptr, compactoffset, skipoffset, r)  \
  r = ((char*)groupptr) + ((long)compactoffset)*sizeof(long) + skipoffset
