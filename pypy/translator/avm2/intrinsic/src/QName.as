package
{
	/// QName objects represent qualified names of XML elements and attributes.
	public class QName extends Object
	{
		public static const length : *;

		/// The local name of the QName object.
		public function get localName () : String;

		/// The Uniform Resource Identifier (URI) of the QName object.
		public function get uri () : *;

		/// Creates a QName object that is a copy of another QName object.
		public function QName (namespace:* = null, name:* = null);

		/// Returns a string composed of the URI, and the local name for the QName object, separated by "::".
		public function toString () : String;

		/// Returns the QName object.
		public function valueOf () : QName;
	}
}
