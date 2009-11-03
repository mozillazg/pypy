package flash.text.engine
{
	/// The JustificationStyle class is an enumeration of constant values for setting the justificationStyle property of the EastAsianJustifier class.
	public class JustificationStyle extends Object
	{
		/// Bases justification on either expanding or compressing the line, whichever gives a result closest to the desired width.
		public static const PRIORITIZE_LEAST_ADJUSTMENT : String;
		/// Bases justification on compressing kinsoku at the end of the line, or expanding it if no kinsoku occurs or if that space is insufficient.
		public static const PUSH_IN_KINSOKU : String;
		/// Bases justification on expanding the line.
		public static const PUSH_OUT_ONLY : String;

		public function JustificationStyle ();
	}
}
