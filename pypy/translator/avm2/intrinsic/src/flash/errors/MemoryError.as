package flash.errors
{
	/// The MemoryError exception is thrown when a memory allocation request fails.
	public class MemoryError extends Error
	{
		/// Creates a new MemoryError object.
		public function MemoryError (message:String = "", id:int = 0);
	}
}
