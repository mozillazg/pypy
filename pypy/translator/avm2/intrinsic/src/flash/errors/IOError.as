package flash.errors
{
	/// The IOError exception is thrown when some type of input or output failure occurs.
	public class IOError extends Error
	{
		/// Creates a new IOError object.
		public function IOError (message:String = "", id:int = 0);
	}
}
