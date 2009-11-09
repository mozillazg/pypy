package flash.errors
{
	/// ActionScript throws a StackOverflowError exception when the stack available to the script is exhausted.
	public class StackOverflowError extends Error
	{
		/// Creates a new StackOverflowError object.
		public function StackOverflowError (message:String = "", id:int = 0);
	}
}
