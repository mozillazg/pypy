package flash.display
{
	/// The SpreadMethod class provides values for the spreadMethod parameter in the beginGradientFill() and lineGradientStyle() methods of the Graphics class.
	public class SpreadMethod extends Object
	{
		/// Specifies that the gradient use the pad spread method.
		public static const PAD : String;
		/// Specifies that the gradient use the reflect spread method.
		public static const REFLECT : String;
		/// Specifies that the gradient use the repeat spread method.
		public static const REPEAT : String;

		public function SpreadMethod ();
	}
}
