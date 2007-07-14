
            import py.*;
            //import py.f.DictIter;


// starts hand written code
var MALLOC_ZERO_FILLED = 0;

var print = trace;




Function.prototype.method = function (name, func) {
    this.prototype[name] = func;
    return this;
};

function inherits(child, parent) {
    child.parent = parent;
    for (var i in parent.prototype) {
        if (!child.prototype[i]) {
            child.prototype[i] = parent.prototype[i];
        }
    }
}

function isinstanceof(self, what) {
    if (!self) {
        return (false);
    }
    var t = self.constructor;
    while ( t ) {
        if (t == what) {
            return (true);
        }
        t = t.parent;
    }
    return (false);
}

/*function delitem(fn, l, i) {
    for(var j = i; j < l.length-1; ++j) {
        l[j] = l[j+1];
    }
    l.length--;
}*/

function strcmp(s1, s2) {
    if ( s1 < s2 ) {
        return ( -1 );
    } else if ( s1 == s2 ) {
        return ( 0 );
    }
    return (1);
}

function startswith(s1, s2) {
    if (s1.length < s2.length) {
        return(false);
    }
    for (var i = 0; i < s2.length; ++i){
        if (s1.charAt(i) != s2.charAt(i)) {
            return(false);
        }
    }
    return(true);
}

function endswith(s1, s2) {
    if (s2.length > s1.length) {
        return(false);
    }
    for (var i = s1.length-s2.length; i < s1.length; ++i) {
        if (s1.charAt(i) != s2.charAt(i - s1.length + s2.length)) {
            return(false);
        }
    }
    return(true);
}

function splitchr(s, ch) {
    var i, lst, next;
    lst = [];
    next = "";
    for (var i = 0; i<s.length; ++i) {
        if (s.charAt(i) == ch) {
            lst.length += 1;
            lst[lst.length-1] = next;
            next = "";
        } else {
            next += s.charAt(i);
        }
    }
    lst.length += 1;
    lst[lst.length-1] = next;
    return (lst);
}


function dict_items_iterator(d) {
    var d2 = new DictIter();
    //var d2 = {};
    var l = [];
    for (var i in d) {
        l.length += 1;
        l[l.length-1] = i;
    }
    d2.l = l;
    d2.current_key = undefined;
    return d2;
}

function get_dict_len(d) {
    var count;
    count = 0;
    for (var i in d) {
        count += 1;
    }
    return (count);
}





function time() {
    var d;
    d = new Date();
    return d/1000;
}

var main_clock_stuff;

function clock() {
    if (main_clock_stuff) {
        //return (new Date() - main_clock_stuff)/1000;
        return 111;
    } else {
        main_clock_stuff = new Date();
        return 0;
    }
}

function substring(s, l, c) {
    return (s.substring(l, l+c));
}

function clear_dict(d) {
    for (var elem in d) {
        delete(d[elem]);
    }
}

function findIndexOf(s1, s2, start, end) {
    if (start > end || start > s1.length) {
        return -1;
    }
    s1 = s1.substr(start, end-start);
    var res = s1.indexOf(s2);
    if (res == -1) {
        return -1;
    }
    return res + start;
}

function findIndexOfTrue(s1, s2) {
    return findIndexOf(s1, s2, 0, s1.length) != -1;
}

function countCharOf(s, c, start, end) {
    s = s.substring(start, end);
    var i = 0;
    for (var c1 in s) {
        if (s[c1] == c) {
            i++;
        }
    }
    return(i);
}

function countOf(s, s1, start, end) {
    var ret = findIndexOf(s, s1, start, end);
    var i = 0;
    var lgt = 1;
    if (s1.length > 0) {
        lgt = s1.length;
    }
    while (ret != -1) {
        i++;
        ret = findIndexOf(s, s1, ret + lgt, end);
    }
    return (i);
}

function convertToString(stuff) {
    if (stuff === undefined) {
       return ("undefined");
    }
    return (stuff.toString());
}    
// ends hand written code
function some_strange_function_which_will_never_be_called () {
    var v1,v2;
    var block = 0;
    for(;;){
        switch(block){
            case 0:
            v1 = 2;
            v2 = xx ( v1 );
            block = 1;
            break;
            case 1:
            return ( undefined );
        }
    }
}

function xx (y_0) {
    var v3,v4;
    var block = 0;
    for(;;){
        switch(block){
            case 0:
            v4 = (y_0+1);
            v3 = v4;
            block = 1;
            break;
            case 1:
            return ( v3 );
        }
    }
}


var __consts_0 = {};
