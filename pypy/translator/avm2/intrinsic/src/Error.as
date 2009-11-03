package
{
	/// The Error class contains information about an error that occurred in a script.
	public class Error extends Object
	{
		public static const length : int;
		/// Contains the message associated with the Error object.
		public var message : *;
		/// Contains the name of the Error object.
		public var name : *;

		/// Contains the reference number associated with the specific error message.
		public function get errorID () : int;

		/// Creates a new Error instance with the specified error message.
		public function Error (message:* = "", id:* = 0);

		public static function getErrorMessage (index:int) : String;

		/// Returns the call stack for an error in a readable form.
		public function getStackTrace () : String;

		public static function throwError (type:Class, index:uint, ...rest) : *;
	}
}
