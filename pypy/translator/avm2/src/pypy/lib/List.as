
package pypy.lib {
    
    public class List extends Array {
        
        public var _TYPE:Class;
        
        public function List(TYPE:Class) {
            _TYPE = TYPE;
        }
        
        public function ll_length():uint {
            return this.length;
        }
        
        public function ll_getitem_fast(index:uint):* {
            return this[index];
        }
        
        public function ll_setitem_fast(index:uint, item:_TYPE):void {
            this[index] = item;
        }
        
        public function toString():String {
            var S:String = "[";
            for each (var i:_TYPE in this) {
                
            }
        }
        
    }
    
}