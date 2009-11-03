package flash.display
{
	/// A class that provides constant values for visual blend mode effects.
	public class BlendMode extends Object
	{
		/// Adds the values of the constituent colors of the display object to the colors of its background, applying a ceiling of 0xFF.
		public static const ADD : String;
		/// Applies the alpha value of each pixel of the display object to the background.
		public static const ALPHA : String;
		/// Selects the darker of the constituent colors of the display object and the colors of the background (the colors with the smaller values).
		public static const DARKEN : String;
		/// Compares the constituent colors of the display object with the colors of its background, and subtracts the darker of the values of the two constituent colors from the lighter value.
		public static const DIFFERENCE : String;
		/// Erases the background based on the alpha value of the display object.
		public static const ERASE : String;
		/// Adjusts the color of each pixel based on the darkness of the display object.
		public static const HARDLIGHT : String;
		/// Inverts the background.
		public static const INVERT : String;
		/// Forces the creation of a transparency group for the display object.
		public static const LAYER : String;
		/// Selects the lighter of the constituent colors of the display object and the colors of the background (the colors with the larger values).
		public static const LIGHTEN : String;
		/// Multiplies the values of the display object constituent colors by the constituent colors of the background color, and normalizes by dividing by 0xFF, resulting in darker colors.
		public static const MULTIPLY : String;
		/// The display object appears in front of the background.
		public static const NORMAL : String;
		/// Adjusts the color of each pixel based on the darkness of the background.
		public static const OVERLAY : String;
		/// Multiplies the complement (inverse) of the display object color by the complement of the background color, resulting in a bleaching effect.
		public static const SCREEN : String;
		/// Uses a shader to define the blend between objects.
		public static const SHADER : String;
		/// Subtracts the values of the constituent colors in the display object from the values of the backgroundcolor, applying a floor of 0.
		public static const SUBTRACT : String;

		public function BlendMode ();
	}
}
