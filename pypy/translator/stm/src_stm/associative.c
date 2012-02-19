
/* parameters taken from my laptop's Core i5, tweaked according to
 * http://en.wikipedia.org/wiki/Haswell_%28microarchitecture%29
 *
 * this is not an optimized implementation at all.  just for measuring
 * the number of collisions that we get on some examples.
 */


#define HWEMULATOR_ASSOCIATIVITY_BITS   3   /* = 8   */
#define HWEMULATOR_CACHE_LINE_BITS      7   /* = 128 */
#define HWEMULATOR_NUMBER_OF_SETS_BITS  6   /* = 64  */

/* this defines a cache size of 64 KB == 1 << (sum of the three numbers) */



typedef struct {
    char data[1 << HWEMULATOR_CACHE_LINE_BITS];
    long tag;
    unsigned long creation;
} cacheline_t;

typedef struct {
    cacheline_t choices[1 << HWEMULATOR_ASSOCIATIVITY_BITS];
}  cacheset_t;

static cacheset_t hwemulator_orecs[1 << HWEMULATOR_NUMBER_OF_SETS_BITS];


static orec_t *get_orec(void* addr)
{
    /* find the set number */
    int setnum = (((long)addr) >> HWEMULATOR_CACHE_LINE_BITS) &
        ((1 << HWEMULATOR_NUMBER_OF_SETS_BITS) - 1);

    /* grab it */
    cacheset_t *set = &hwemulator_orecs[setnum];

    /* round down the addr to get the tag */
    long tag = ((long)addr) >> HWEMULATOR_CACHE_LINE_BITS;

    /* is the cacheline already in the set? */
    int i;
    cacheline_t *line;
    for (i=0; i < (1 << HWEMULATOR_ASSOCIATIVITY_BITS); i++) {
        line = &set->choices[i];
        if (line->tag == tag)
            goto found;
    }

    /* find the oldest cacheline in the set */
    cacheline_t *oldest_line = 0;
    unsigned long oldest = (unsigned long) -1;
    unsigned long youngest = 0;
    for (i=0; i < (1 << HWEMULATOR_ASSOCIATIVITY_BITS); i++) {
        line = &set->choices[i];
        if (line->creation < oldest) {
            oldest = line->creation;
            oldest_line = line;
        }
        if (line->creation > youngest)
            youngest = line->creation;
    }

    /* replace it */
    line = oldest_line;
    line->tag = tag;
    line->creation = youngest + 1;
    /* XXX this is wrong!! it can evict a line containing relevant data,
       which can then be recreated at a different index!  The issue is
       that this operation may forget that we did some changes!  But
       it's probably good enough for now just to measure the effect */

 found:;
    /* return the orec_t that is in line->data at the correct offset */
    assert((((long)addr) & (sizeof(orec_t)-1)) == 0);
    char *p = line->data + (((long)addr) &
                            ((1 << HWEMULATOR_CACHE_LINE_BITS) - 1));
    return (orec_t *)p;
}
