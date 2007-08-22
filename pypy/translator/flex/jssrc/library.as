_consts_0.convertToString = function (stuff) {
            if (stuff === undefined) {
               return ("undefined");
            }
            return (stuff.toString());
            }  
_consts_0.flexTrace = function ( text:String ):void {
    var myUrl:URLRequest = new URLRequest("javascript:console.log('" + text + "');void(0);");
    sendToURL(myUrl);
}

// wrapper for throw, because flex compiler weirdness.
_consts_0.throwit = function (e) {
    throw(e);
}

_consts_0.inherits = function (child, parent) {
    child.parent = parent;
    for (var i in parent.prototype) {
        if (!child.prototype[i]) {
            child.prototype[i] = parent.prototype[i];
        }
    }
}

_consts_0.isinstanceof = function (self, what) {

    //return self instanceof what;


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

_consts_0.strcmp = function (s1, s2) {
    if ( s1 < s2 ) {
        return ( -1 );
    } else if ( s1 == s2 ) {
        return ( 0 );
    }
    return (1);
}

_consts_0.startswith = function (s1, s2) {
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

_consts_0.endswith = function (s1, s2) {
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

_consts_0.splitchr = function (s, ch) {
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


_consts_0.dict_items_iterator = function (d) {
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

_consts_0.get_dict_len = function (d) {
    var count;
    count = 0;
    for (var i in d) {
        count += 1;
    }
    return (count);
}





_consts_0.time = function () {
    var d;
    d = new Date();
    return d/1000;
}

_consts_0.main_clock_stuff = false;

_consts_0.clock = function () {
    if (_consts_0.main_clock_stuff) {
        //return (new Date() - main_clock_stuff)/1000;
        return 111;
    } else {
        _consts_0.main_clock_stuff = new Date();
        return 0;
    }
}

_consts_0.substring = function (s, l, c) {
    return (s.substring(l, l+c));
}

_consts_0.clear_dict = function (d) {
    for (var elem in d) {
        delete(d[elem]);
    }
}

_consts_0.findIndexOf = function (s1, s2, start, end) {
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

_consts_0.findIndexOfTrue = function (s1, s2) {
    return _consts_0.findIndexOf(s1, s2, 0, s1.length) != -1;
}

_consts_0.countCharOf = function (s, c, start, end) {
    s = s.substring(start, end);
    var i = 0;
    for (var c1 in s) {
        if (s[c1] == c) {
            i++;
        }
    }
    return(i);
}

_consts_0.countOf = function (s, s1, start, end) {
    var ret = _consts_0.findIndexOf(s, s1, start, end);
    var i = 0;
    var lgt = 1;
    if (s1.length > 0) {
        lgt = s1.length;
    }
    while (ret != -1) {
        i++;
        ret = _consts_0.findIndexOf(s, s1, ret + lgt, end);
    }
    return (i);
}
   
