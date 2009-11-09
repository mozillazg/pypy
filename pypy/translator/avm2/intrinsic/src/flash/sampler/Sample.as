package flash.sampler
{
	/// The Sample class creates objects that hold memory analysis information over distinct durations.
	public class Sample extends Object
	{
		/// Contains information about the methods executed by Flash Player over a specified period of time.
		public const stack : Array;
		/// The microseconds that define the duration of the Sample instance.
		public const time : Number;

		public function Sample ();
	}
}
