package py {


dynamic public class StringBuilder {

    public function StringBuilder() {
        this.l = [];
    }

    function ll_append_char(s) {
        this.l.length += 1;
        this.l[this.l.length - 1] = s;
    }

    function ll_append(s) {
        this.l.push(s);
    }

    function ll_allocate(t) {
    }

    function ll_build() {
        var s;
        s = "";
        for (var i in this.l) {
            s += this.l[i];
        }
        return (s);
    }

}

}
