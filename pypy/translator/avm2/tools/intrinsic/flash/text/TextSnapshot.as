package flash.text
{
	/// TextSnapshot objects let you work with static text in a movie clip.
	public class TextSnapshot extends Object
	{
		/// The number of characters in a TextSnapshot object.
		public function get charCount () : int;

		/// Searches the specified TextSnapshot object and returns the position of the first occurrence of textToFind found at or after beginIndex.
		public function findText (beginIndex:int, textToFind:String, caseSensitive:Boolean) : int;

		/// Returns a Boolean value that specifies whether a TextSnapshot object contains selected text in the specified range.
		public function getSelected (beginIndex:int, endIndex:int) : Boolean;

		/// Returns a string that contains all the characters specified by the corresponding setSelected() method.
		public function getSelectedText (includeLineEndings:Boolean = false) : String;

		/// Returns a string that contains all the characters specified by the beginIndex and endIndex parameters.
		public function getText (beginIndex:int, endIndex:int, includeLineEndings:Boolean = false) : String;

		/// Returns an array of objects that contains information about a run of text.
		public function getTextRunInfo (beginIndex:int, endIndex:int) : Array;

		/// Lets you determine which character within a TextSnapshot object is on or near the specified x, y coordinates of the movie clip containing the text in the TextSnapshot object.
		public function hitTestTextNearPos (x:Number, y:Number, maxDistance:Number = 0) : Number;

		/// Specifies the color to use when highlighting characters that have been selected with the  setSelected() method.
		public function setSelectColor (hexColor:uint = 16776960) : void;

		/// Specifies a range of characters in a TextSnapshot object to be selected or deselected.
		public function setSelected (beginIndex:int, endIndex:int, select:Boolean) : void;

		public function TextSnapshot ();
	}
}
