package flash.text
{
	/// The CSMSettings class contains properties for use with the TextRenderer.setAdvancedAntiAliasingTable() method to provide continuous stroke modulation (CSM).
	public class CSMSettings extends Object
	{
		/// The size, in pixels, for which the settings apply.
		public var fontSize : Number;
		/// The inside cutoff value, above which densities are set to a maximum density value (such as 255).
		public var insideCutoff : Number;
		/// The outside cutoff value, below which densities are set to zero.
		public var outsideCutoff : Number;

		/// Creates a new CSMSettings object which stores stroke values for custom anti-aliasing settings.
		public function CSMSettings (fontSize:Number, insideCutoff:Number, outsideCutoff:Number);
	}
}
