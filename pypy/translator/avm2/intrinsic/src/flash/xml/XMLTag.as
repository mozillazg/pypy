package flash.xml
{
	public class XMLTag extends Object
	{
		public function get attrs () : Object;
		public function set attrs (value:Object) : void;

		public function get empty () : Boolean;
		public function set empty (value:Boolean) : void;

		public function get type () : uint;
		public function set type (value:uint) : void;

		public function get value () : String;
		public function set value (v:String) : void;

		public function XMLTag ();
	}
}
