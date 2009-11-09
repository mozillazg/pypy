package adobe.utils
{
	import flash.events.EventDispatcher;

	public class ProductManager extends EventDispatcher
	{
		public function get installed () : Boolean;

		public function get installedVersion () : String;

		public function get running () : Boolean;

		public function download (caption:String = null, fileName:String = null, pathElements:Array = null) : Boolean;

		public function launch (parameters:String = null) : Boolean;

		public function ProductManager (name:String);
	}
}
