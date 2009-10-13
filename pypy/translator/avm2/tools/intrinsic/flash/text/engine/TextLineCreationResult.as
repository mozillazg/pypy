package flash.text.engine
{
	/// The TextLineCreationResult class is an enumeration of constant values used with TextBlock.textLineCreationResult.
	public class TextLineCreationResult extends Object
	{
		/// Indicates no line was created because all text in the block had already been broken.
		public static const COMPLETE : String;
		/// Indicates the line was created with an emergency break because no break opportunity was available in the specified width.
		public static const EMERGENCY : String;
		/// Indicates no line was created because no text could fit in the specified width and fitSomething was not specified in the call to createTextLine().
		public static const INSUFFICIENT_WIDTH : String;
		/// Indicates the line was successfully broken.
		public static const SUCCESS : String;

		public function TextLineCreationResult ();
	}
}
