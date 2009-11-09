package flash.text.engine
{
	/// The TextBaseline class is an enumeration of constant values to use in setting the dominantBaseline andalignmentBaseline properties of the ElementFormat class.
	public class TextBaseline extends Object
	{
		/// Specifies an ascent baseline.
		public static const ASCENT : String;
		/// Specifies a descent baseline.
		public static const DESCENT : String;
		/// Specifies an ideographic bottom baseline.
		public static const IDEOGRAPHIC_BOTTOM : String;
		/// Specifies an ideographic center baseline.
		public static const IDEOGRAPHIC_CENTER : String;
		/// Specifies an ideographic top baseline.
		public static const IDEOGRAPHIC_TOP : String;
		/// Specifies a roman baseline.
		public static const ROMAN : String;
		/// Specifies that the alignmentBaseline is the same as the dominantBaseline.
		public static const USE_DOMINANT_BASELINE : String;

		public function TextBaseline ();
	}
}
