package flash.text.engine
{
	import flash.text.engine.TextLine;
	import flash.geom.Rectangle;
	import flash.text.engine.TextLineMirrorRegion;
	import flash.text.engine.ContentElement;
	import flash.events.EventDispatcher;

	/// The TextLineMirrorRegion class represents a portion of a text line wherein events are mirrored to another event dispatcher.
	public class TextLineMirrorRegion extends Object
	{
		/// The bounds of the mirror region, relative to the text line.
		public function get bounds () : Rectangle;

		/// The ContentElement object from which the mirror region was derived.
		public function get element () : ContentElement;

		/// The EventDispatcher object to which events affecting the mirror region are mirrored.
		public function get mirror () : EventDispatcher;

		/// The next TextLineMirrorRegion in the set derived from the text element, or null if the current region is the last mirror region in the set.
		public function get nextRegion () : TextLineMirrorRegion;

		/// The previous TextLineMirrorRegion in the set derived from the text element, or null if the current region is the first mirror region in the set.
		public function get previousRegion () : TextLineMirrorRegion;

		/// The TextLine containing this mirror region.
		public function get textLine () : TextLine;

		public function TextLineMirrorRegion ();
	}
}
