
package pypy.lib {
    
    import flash.utils.Dictionary;
    
    public class Dict extends Dictionary {
        
        public var _KEY:Class;
        public var _VAL:Class;
        
        public function Dict(KEY_TYPE:Class, VAL_TYPE:Class) {
            this._KEY = KEY_TYPE;
            this._VAL = VAL_TYPE;
        }
        
        public function ll_length():int {
            var n:int = 0;
            for(var i:_KEY in this) n ++;
            return n;
        }
        
        public function ll_get(key:_KEY):_VAL {
            return this[key];
        }
        
        public function ll_set(key:_KEY, value:_VAL):void {
            this[key] = value;
        }
        
        public function ll_remove(key:_KEY):void {
            delete this[key];
            this[key] = null;
        }
        
        public function ll_contains(key:_KEY):void {
            return this[key] != null;
        }
        
        public function ll_clear():void {
            for (var i:* in this) ll_remove(i);
        }

        public function ll_copy():Dict {
            var res:Dict = new Dict();
            for (var key:_KEY in this) res[key] = this[key];
            return res;
        }
        
    }
    
}