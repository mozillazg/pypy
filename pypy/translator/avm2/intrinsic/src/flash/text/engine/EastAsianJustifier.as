package flash.text.engine
{
	import flash.text.engine.TextJustifier;

	/// The EastAsianJustifier class has properties to control the justification options for text lines whose content is primarily East Asian text.
	public class EastAsianJustifier extends TextJustifier
	{
		/// Specifies the justification style for the text in a text block.
		public function get justificationStyle () : String;
		public function set justificationStyle (value:String) : void;

		/// Constructs a cloned copy of the EastAsianJustifier.
		public function clone () : TextJustifier;

		/// Creates a EastAsianJustifier object.
		public function EastAsianJustifier (locale:String = "ja", lineJustification:String = "allButLast", justificationStyle:String = "pushInKinsoku");
	}
}
