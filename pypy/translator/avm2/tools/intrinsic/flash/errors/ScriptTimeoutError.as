package flash.errors
{
	/// The ScriptTimeoutError exception is thrown when the script timeout interval is reached.
	public class ScriptTimeoutError extends Error
	{
		/// Creates a new ScriptTimeoutError object.
		public function ScriptTimeoutError (message:String = "", id:int = 0);
	}
}
