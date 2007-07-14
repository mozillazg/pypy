
package py {

public class DictIter {

    var current_key;
    var l;

    public function DictIter() {
        this.current_key = null;
    }

    function ll_go_next() {
        var ret = this.l.length != 0;
        this.current_key = this.l.pop();
        return ret;
    }

    function ll_current_key() {
        if (this.current_key) {
            return this.current_key;
        } else {
            return null;
        }
    }

}



}
