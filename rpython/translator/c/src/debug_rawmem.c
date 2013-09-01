#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <assert.h>

#include "common_header.h"


#ifdef RPY_LL_ASSERT

#include "src/debug_rawmem.h"


#if PYPY_LONG_BIT == 32
#define RANDOM_MASK    3645261274UL
#else
#define RANDOM_MASK    648108117509314956UL
#endif


struct debugtreenode_s {
    void *base;
    Signed length;
    struct debugtreenode_s *left, *right;
};

static struct debugtreenode_s *debugtreeroot = NULL;


static Signed debugtreenode_key(void *base)
{
    return ((Signed)base) ^ RANDOM_MASK;
}

static struct debugtreenode_s **debugtreenode_lookup_starting_at(void *base,
                                                 struct debugtreenode_s **pp)
{
    Signed key = debugtreenode_key(base);
    while (*pp != NULL) {
        Signed nodekey = debugtreenode_key((*pp)->base);
        if (key < nodekey)
            pp = &(*pp)->left;
        else if (key > nodekey)
            pp = &(*pp)->right;
        else
            break;
    }
    return pp;
}

static struct debugtreenode_s **debugtreenode_lookup(void *base)
{
    return debugtreenode_lookup_starting_at(base, &debugtreeroot);
}

void RPyRawMalloc_Record_Size(void *base, Signed length)
{
    if (base == NULL)
        return;
    struct debugtreenode_s **pp = debugtreenode_lookup(base);
    struct debugtreenode_s *p = *pp;
    if (p == NULL) {
        p = malloc(sizeof(struct debugtreenode_s));
        if (p == NULL)
            return;     /* too bad */
        p->base = base;
        p->left = NULL;
        p->right = NULL;
        *pp = p;
    }
    else {
        fprintf(stderr, "_RPyRawMalloc_Record_Size: 'base' is already "
                        "recorded.  Something went wrong.\n");
    }
    p->length = length;
}

void RPyRawMalloc_Forget_Size(void *base)
{
    if (base == NULL)
        return;
    struct debugtreenode_s **pp = debugtreenode_lookup(base);
    struct debugtreenode_s *p = *pp;
    struct debugtreenode_s *reattach = NULL;
    if (p == NULL)
        return;     /* not here */

    if (p->left) {
        pp = &p->left;
        while ((*pp)->right != NULL)
            pp = &(*pp)->right;
        p->base = (*pp)->base;
        p->length = (*pp)->length;
        reattach = (*pp)->left;
    }
    else if (p->right) {
        pp = &p->right;
        while ((*pp)->left != NULL)
            pp = &(*pp)->left;
        p->base = (*pp)->base;
        p->length = (*pp)->length;
        reattach = (*pp)->right;
    }
    free(*pp);
    *pp = reattach;
}

Signed RPyRawMalloc_Size(void *base)
{
    assert(base != NULL);
    struct debugtreenode_s **pp = debugtreenode_lookup(base);
    if (*pp != NULL)
        return (*pp)->length;
    else
        return LONG_MAX;
}

#endif
