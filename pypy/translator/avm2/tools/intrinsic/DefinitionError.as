package
{
	/// The DefinitionError class represents an error that occurs when user code attempts to define an identifier that is already defined.
	public class DefinitionError extends Error
	{
		public static const length : int;

		/// Creates a new DefinitionError object.
		public function DefinitionError (message:* = "", id:* = 0);
	}
}
