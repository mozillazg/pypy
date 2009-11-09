package flash.text.engine
{
	/// The TabStop class represents the properties of a tab stop in a text block.
	public class TabStop extends Object
	{
		/// Specifies the tab alignment for this tab stop.
		public function get alignment () : String;
		public function set alignment (value:String) : void;

		/// Specifies the alignment token to use when you set the alignment property to TabAlignment.DECIMAL.
		public function get decimalAlignmentToken () : String;
		public function set decimalAlignmentToken (value:String) : void;

		/// The position of the tab stop, in pixels, relative to the start of the text line.
		public function get position () : Number;
		public function set position (value:Number) : void;

		/// Creates a new TabStop.
		public function TabStop (alignment:String = "start", position:Number = 0, decimalAlignmentToken:String = "");
	}
}
