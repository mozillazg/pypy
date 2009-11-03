package
{
	/// A Boolean object is a data type that can have one of two values, either true or false, used for logical operations.
	public class Boolean extends Object
	{
		public static const length : int;

		/// Creates a Boolean object with the specified value.
		public function Boolean (value:* = null);

		/// Returns the string representation ("true" or "false") of the Boolean object.
		public function toString () : String;

		/// Returns true if the value of the specified Boolean object is true; false otherwise.
		public function valueOf () : Boolean;
	}
}
