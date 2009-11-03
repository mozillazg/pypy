package flash.filters
{
	import flash.filters.BitmapFilter;

	/// The BitmapFilter class is the base class for all image filter effects.
	public class BitmapFilter extends Object
	{
		public function BitmapFilter ();

		/// A copy of the BitmapFilter object.
		public function clone () : BitmapFilter;
	}
}
