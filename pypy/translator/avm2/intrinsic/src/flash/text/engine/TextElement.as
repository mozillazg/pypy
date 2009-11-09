package flash.text.engine
{
	import flash.text.engine.ElementFormat;
	import flash.events.EventDispatcher;

	/// The TextElement class represents a string of formatted text.
	public class TextElement extends ContentElement
	{
		/// Receives the text that is the content of the element.
		public function set text (value:String) : void;

		/// Replaces the range of characters that the beginIndex and endIndex parameters specify with the contents of the newText parameter.
		public function replaceText (beginIndex:int, endIndex:int, newText:String) : void;

		/// Creates a new TextElement instance.
		public function TextElement (text:String = null, elementFormat:ElementFormat = null, eventMirror:EventDispatcher = null, textRotation:String = "rotate0");
	}
}
