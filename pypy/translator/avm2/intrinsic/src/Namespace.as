package
{
	/// The Namespace class contains methods and properties for defining and working with namespaces.
	public class Namespace extends Object
	{
		public static const length : *;

		/// The prefix of the namespace.
		public function get prefix () : *;

		/// The Uniform Resource Identifier (URI) of the namespace.
		public function get uri () : String;

		/// Creates a Namespace object, given the prefixValue and uriValue.
		public function Namespace (prefix:* = null, uri:* = null);

		/// Equivalent to the Namespace.uri property.
		public function toString () : String;

		/// Equivalent to the Namespace.uri property.
		public function valueOf () : String;
	}
}
