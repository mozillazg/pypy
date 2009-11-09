package
{
	/// A function is the basic unit of code that can be invoked in ActionScript.
	public class Function extends Object
	{
		public static const length : int;

		public function get length () : int;

		public function get prototype () : *;
		public function set prototype (p:*) : void;

		/// Specifies the object instance on which the Function is called.
		public function apply (thisArg:* = null, argArray:* = null) : *;

		/// Invokes this Function.
		public function call (thisArg:* = null, ...rest) : *;

		public function Function ();
	}
}
