package flash.sampler
{
	/// The DeleteObjectSample class represents objects that are created within a getSamples() stream; each DeleteObjectSample object corresponds to a NewObjectSample object.
	public class DeleteObjectSample extends Sample
	{
		/// The unique identification number that matches up with a NewObjectSample's identification number.
		public const id : Number;
		/// The size of the DeleteObjectSample object before it is deleted.
		public const size : Number;

		public function DeleteObjectSample ();
	}
}
