package flash.errors
{
	/// The IllegalOperationError exception is thrown when a method is not implemented or the implementation doesn't cover the current usage.
	public class IllegalOperationError extends Error
	{
		/// Creates a new IllegalOperationError object.
		public function IllegalOperationError (message:String = "", id:int = 0);
	}
}
