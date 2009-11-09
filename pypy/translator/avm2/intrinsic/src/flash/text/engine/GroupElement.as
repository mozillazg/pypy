package flash.text.engine
{
	import flash.text.engine.ContentElement;
	import flash.text.engine.TextElement;
	import flash.text.engine.GroupElement;
	import flash.text.engine.ElementFormat;
	import flash.events.EventDispatcher;

	/// A GroupElement object groups a collection of TextElement, GraphicElement, or other GroupElement objects that you can assign as a whole to the content property of a TextBlock object.
	public class GroupElement extends ContentElement
	{
		/// The number of elements in the group.
		public function get elementCount () : int;

		/// Retrieves an element from within the group.
		public function getElementAt (index:int) : ContentElement;

		/// Returns the element containing the character specified by the charIndex parameter.
		public function getElementAtCharIndex (charIndex:int) : ContentElement;

		/// Returns the index of the element specified by the element parameter.
		public function getElementIndex (element:ContentElement) : int;

		/// Creates a new GroupElement instance.
		public function GroupElement (elements:Vector.<ContentElement> = null, elementFormat:ElementFormat = null, eventMirror:EventDispatcher = null, textRotation:String = "rotate0");

		/// Replaces the range of elements that the beginIndex and endIndex parameters specify with a new GroupElement containing those elements.
		public function groupElements (beginIndex:int, endIndex:int) : GroupElement;

		/// Merges the text from the range of elements that the beginIndex and endIndex parameters specify into the element specified by beginIndex without affecting the format of that element.
		public function mergeTextElements (beginIndex:int, endIndex:int) : TextElement;

		/// Replaces the range of elements that the beginIndex and endIndex parameters specify with the contents of the newElements parameter.
		public function replaceElements (beginIndex:int, endIndex:int, newElements:Vector.<ContentElement>) : Vector.<ContentElement>;

		/// Sets the elements in the group to the contents of the Vector.
		public function setElements (value:Vector.<ContentElement>) : void;

		/// Splits a portion of a TextElement in the group into a new TextElement which is inserted into the group following the specified TextElement.
		public function splitTextElement (elementIndex:int, splitIndex:int) : TextElement;

		/// Ungroups the elements in a nested GroupElement that groupIndex specifies within an outer GroupElement object.
		public function ungroupElements (groupIndex:int) : void;
	}
}
