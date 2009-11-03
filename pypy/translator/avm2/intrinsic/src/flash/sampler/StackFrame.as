package flash.sampler
{
	/// The StackFrame class provides access to the properties of a data block containing a function.
	public class StackFrame extends Object
	{
		/// The file name of the SWF file being debugged.
		public const file : String;
		/// The line number for the function in the SWF file being debugged.
		public const line : uint;
		/// The function name in the stack frame.
		public const name : String;

		public function StackFrame ();

		/// Converts the StackFrame to a string of its properties.
		public function toString () : String;
	}
}
