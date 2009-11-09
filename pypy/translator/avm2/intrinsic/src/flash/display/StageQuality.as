package flash.display
{
	/// The StageQuality class provides values for the Stage.quality property.
	public class StageQuality extends Object
	{
		/// Specifies very high rendering quality: graphics are anti-aliased using a 4 x 4 pixel grid and bitmaps are always smoothed.
		public static const BEST : String;
		/// Specifies high rendering quality: graphics are anti-aliased using a 4 x 4 pixel grid, and bitmaps are smoothed if the movie is static.
		public static const HIGH : String;
		/// Specifies low rendering quality: graphics are not anti-aliased, and bitmaps are not smoothed.
		public static const LOW : String;
		/// Specifies medium rendering quality: graphics are anti-aliased using a 2 x 2 pixel grid, but bitmaps are not smoothed.
		public static const MEDIUM : String;

		public function StageQuality ();
	}
}
