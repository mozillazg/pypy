/************************************************************/
/***  C header subsection: operations between addresses   ***/

/*** unary operations ***/

/***  binary operations ***/

#define OP_ADR_DELTA(x,y,r) r = ((char *)(x) - (char *)(y))
#define OP_ADR_SUB(x,y,r)   r = ((char *)(x) - (y))
#define OP_ADR_ADD(x,y,r)   r = ((char *)(x) + (y))

#define OP_ADR_EQ(x,y,r)	  r = ((x) == (y))
#define OP_ADR_NE(x,y,r)	  r = ((x) != (y))
#define OP_ADR_LE(x,y,r)	  r = ((x) <= (y))
#define OP_ADR_GT(x,y,r)	  r = ((x) >  (y))
#define OP_ADR_LT(x,y,r)	  r = ((x) <  (y))
#define OP_ADR_GE(x,y,r)	  r = ((x) >= (y))

#define OP_CAST_ADR_TO_INT(x, r)     r = ((long)x)
#define OP_CAST_INT_TO_ADR(x, r)     r = ((void *)(x))

/* XXX assumes that addresses fit in a long */
#define OP_ADR_OR(x,y,r)    r = (char *)((long)(x) | (y))
#define OP_ADR_AND(x,y,r)   r = (char *)((long)(x) & (y))
