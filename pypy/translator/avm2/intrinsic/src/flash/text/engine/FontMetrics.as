package flash.text.engine
{
	import flash.geom.Rectangle;

	/// The FontMetrics class contains measurement and offset information about a font.
	public class FontMetrics extends Object
	{
		/// The emBox value represents the design space of the font and is used to place Chinese, Korean, or Japanese glyphs relative to the Roman baseline.
		public var emBox : Rectangle;
		/// The strikethroughOffset value is the suggested vertical offset from the Roman baseline for a strikethrough.
		public var strikethroughOffset : Number;
		/// The strikethroughThickness value is the suggested thickness for a strikethrough.
		public var strikethroughThickness : Number;
		/// The subscriptOffset value is the suggested vertical offset from the Roman baseline for a subscript.
		public var subscriptOffset : Number;
		/// The subscriptScale value is the suggested scale factor to apply to the point size for a subscript.
		public var subscriptScale : Number;
		/// The superscriptOffset value is the suggested vertical offset from the Roman baseline for a superscript.
		public var superscriptOffset : Number;
		/// The superscriptScale value is the suggested scale factor to apply to the point size for a superscript.
		public var superscriptScale : Number;
		/// The underlineOffset value is the suggested vertical offset from the Roman baseline for an underline.
		public var underlineOffset : Number;
		/// The underlineThickness value is the suggested thickness for an underline.
		public var underlineThickness : Number;

		/// Creates a FontMetrics object.
		public function FontMetrics (emBox:Rectangle, strikethroughOffset:Number, strikethroughThickness:Number, underlineOffset:Number, underlineThickness:Number, subscriptOffset:Number, subscriptScale:Number, superscriptOffset:Number, superscriptScale:Number);
	}
}
