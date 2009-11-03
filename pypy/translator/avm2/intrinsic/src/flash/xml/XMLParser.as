package flash.xml
{
	import flash.xml.XMLTag;

	public class XMLParser extends Object
	{
		public function getNext (tag:XMLTag) : int;

		public function startParse (source:String, ignoreWhite:Boolean) : void;

		public function XMLParser ();
	}
}
