
package pypy.lib {
    
    import flash.utils.getQualifiedClassName;
    
    public class Result {
        
        public static function InstanceToPython(obj:Object):String {
            return "InstanceWrapper('" + getQualifiedClassName(obj) + "')";
        }
        
    }
    
}