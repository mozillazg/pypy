package flash.text
{
	/// The TextLineMetrics class contains information about the text position and measurements of a line of text within a text field.
	public class TextLineMetrics extends Object
	{
		/// The ascent value of the text is the length from the baseline to the top of the line height in pixels.
		public var ascent : Number;
		/// The descent value of the text is the length from the baseline to the bottom depth of the line in pixels.
		public var descent : Number;
		/// The height value of the text of the selected lines (not necessarily the complete text) in pixels.
		public var height : Number;
		/// The leading value is the measurement of the vertical distance between the lines of text.
		public var leading : Number;
		/// The width value is the width of the text of the selected lines (not necessarily the complete text) in pixels.
		public var width : Number;
		/// The x value is the left position of the first character in pixels.
		public var x : Number;

		/// Contains information about the text position and measurements of a line of text in a text field.
		public function TextLineMetrics (x:Number, width:Number, height:Number, ascent:Number, descent:Number, leading:Number);
	}
}
