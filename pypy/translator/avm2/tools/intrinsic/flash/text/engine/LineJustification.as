package flash.text.engine
{
	/// The LineJustification class is an enumeration of constant values used in setting the lineJustfication property of the TextJustifier subclasses.
	public class LineJustification extends Object
	{
		/// Directs the text engine to justify all but the last line.
		public static const ALL_BUT_LAST : String;
		/// Directs the text engine to justify all lines.
		public static const ALL_INCLUDING_LAST : String;
		/// Directs the text engine to generate unjustified lines.
		public static const UNJUSTIFIED : String;

		public function LineJustification ();
	}
}
