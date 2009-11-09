package flash.text.engine
{
	import flash.text.engine.TextBlock;
	import flash.text.engine.ElementFormat;
	import flash.events.EventDispatcher;
	import flash.text.engine.GroupElement;

	/// The ContentElement class serves as a base class for the element types that can appear in a GroupElement, namely a GraphicElement, another GroupElement, or a TextElement.
	public class ContentElement extends Object
	{
		/// Indicates the presence a graphic element in the text.
		public static const GRAPHIC_ELEMENT : uint;
		/// Provides a way for the author to associate arbitrary data with the element.
		public var userData : *;

		/// The ElementFormat object used for the element.
		public function get elementFormat () : ElementFormat;
		public function set elementFormat (value:ElementFormat) : void;

		/// The EventDispatcher object that receives copies of every event dispatched to valid text lines based on this content element.
		public function get eventMirror () : EventDispatcher;
		public function set eventMirror (value:EventDispatcher) : void;

		/// The GroupElement object that contains this element, or null if it is not in a group.
		public function get groupElement () : GroupElement;

		/// A copy of the text in the element, including the U+FDEF characters.
		public function get rawText () : String;

		/// A copy of the text in the element, not including the U+FDEF characters, which represent graphic elements in the String.
		public function get text () : String;

		/// The TextBlock to which this element belongs.
		public function get textBlock () : TextBlock;

		/// The index in the text block of the first character of this element.
		public function get textBlockBeginIndex () : int;

		/// The rotation to apply to the element as a unit.
		public function get textRotation () : String;
		public function set textRotation (value:String) : void;

		/// Calling the new ContentElement() constructor throws an ArgumentError exception.
		public function ContentElement (elementFormat:ElementFormat = null, eventMirror:EventDispatcher = null, textRotation:String = "rotate0");
	}
}
