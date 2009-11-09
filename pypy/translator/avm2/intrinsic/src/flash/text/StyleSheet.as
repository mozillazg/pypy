package flash.text
{
	import flash.events.EventDispatcher;
	import flash.text.TextFormat;

	/// The StyleSheet class lets you create a StyleSheet object that contains text formatting rules for font size, color, and other styles.
	public class StyleSheet extends EventDispatcher
	{
		/// An array that contains the names (as strings) of all of the styles registered in this style sheet.
		public function get styleNames () : Array;

		/// Removes all styles from the style sheet object.
		public function clear () : void;

		/// Returns a copy of the style object associated with the style named styleName.
		public function getStyle (styleName:String) : Object;

		/// Parses the CSS in cssText and loads the StyleSheet with it.
		public function parseCSS (CSSText:String) : void;

		/// Adds a new style with the specified name to the style sheet object.
		public function setStyle (styleName:String, styleObject:Object) : void;

		/// Creates a new StyleSheet object.
		public function StyleSheet ();

		/// Extends the CSS parsing capability.
		public function transform (formatObject:Object) : TextFormat;
	}
}
