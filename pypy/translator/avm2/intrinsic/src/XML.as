package
{
	/// The XML class contains methods and properties for working with XML objects.
	public class XML extends Object
	{
		/// For XML objects, this method always returns the integer 1.
		public static const length : *;

		/// Determines whether XML comments are ignored when XML objects parse the source XML data.
		public static function get ignoreComments () : Boolean;
		public static function set ignoreComments (newIgnore:Boolean) : void;

		/// Determines whether XML processing instructions are ignored when XML objects parse the source XML data.
		public static function get ignoreProcessingInstructions () : Boolean;
		public static function set ignoreProcessingInstructions (newIgnore:Boolean) : void;

		/// Determines whether white space characters at the beginning and end of text nodes are ignored during parsing.
		public static function get ignoreWhitespace () : Boolean;
		public static function set ignoreWhitespace (newIgnore:Boolean) : void;

		/// Determines the amount of indentation applied by the toString() and toXMLString() methods when the XML.prettyPrinting property is set to true.
		public static function get prettyIndent () : int;
		public static function set prettyIndent (newIndent:int) : void;

		/// Determines whether the toString() and toXMLString() methods normalize white space characters between some tags.
		public static function get prettyPrinting () : Boolean;
		public static function set prettyPrinting (newPretty:Boolean) : void;

		/// Adds a namespace to the set of in-scope namespaces for the XML object.
		public function addNamespace (ns:*) : XML;

		/// Appends the given child to the end of the XML object's properties.
		public function appendChild (child:*) : XML;

		/// Returns the XML value of the attribute that has the name matching the attributeName parameter.
		public function attribute (arg:*) : XMLList;

		/// Returns a list of attribute values for the given XML object.
		public function attributes () : XMLList;

		/// Lists the children of an XML object.
		public function child (propertyName:*) : XMLList;

		/// Identifies the zero-indexed position of this XML object within the context of its parent.
		public function childIndex () : int;

		/// Lists the children of the XML object in the sequence in which they appear.
		public function children () : XMLList;

		/// Lists the properties of the XML object that contain XML comments.
		public function comments () : XMLList;

		/// Compares the XML object against the given value parameter.
		public function contains (value:*) : Boolean;

		/// Returns a copy of the given XML object.
		public function copy () : XML;

		/// Returns an object with the following properties set to the default values: ignoreComments, ignoreProcessingInstructions, ignoreWhitespace, prettyIndent, and prettyPrinting.
		public static function defaultSettings () : Object;

		/// Returns all descendants (children, grandchildren, great-grandchildren, and so on) of the XML object that have the given name parameter.
		public function descendants (name:* = "*") : XMLList;

		/// Lists the elements of an XML object.
		public function elements (name:* = "*") : XMLList;

		/// Checks to see whether the XML object contains complex content.
		public function hasComplexContent () : Boolean;

		/// Checks to see whether the object has the property specified by the p parameter.
		public function hasOwnProperty (P:* = null) : Boolean;

		/// Checks to see whether the XML object contains simple content.
		public function hasSimpleContent () : Boolean;

		/// Lists the namespaces for the XML object, based on the object's parent.
		public function inScopeNamespaces () : Array;

		/// Inserts the given child2 parameter after the child1 parameter in this XML object and returns the resulting object.
		public function insertChildAfter (child1:*, child2:*) : *;

		/// Inserts the given child2 parameter before the child1 parameter in this XML object and returns the resulting object.
		public function insertChildBefore (child1:*, child2:*) : *;

		public function length () : int;

		/// Gives the local name portion of the qualified name of the XML object.
		public function localName () : Object;

		/// Gives the qualified name for the XML object.
		public function name () : Object;

		/// If no parameter is provided, gives the namespace associated with the qualified name of this XML object.
		public function namespace (prefix:* = null) : *;

		/// Lists namespace declarations associated with the XML object in the context of its parent.
		public function namespaceDeclarations () : Array;

		/// Specifies the type of node: text, comment, processing-instruction, attribute, or element.
		public function nodeKind () : String;

		/// For the XML object and all descendant XML objects, merges adjacent text nodes and eliminates empty text nodes.
		public function normalize () : XML;

		public function notification () : Function;

		/// Returns the parent of the XML object.
		public function parent () : *;

		/// Inserts a copy of the provided child object into the XML element before any existing XML properties for that element.
		public function prependChild (value:*) : XML;

		/// If a name parameter is provided, lists all the children of the XML object that contain processing instructions with that name.
		public function processingInstructions (name:* = "*") : XMLList;

		/// Checks whether the property p is in the set of properties that can be iterated in a for..in statement applied to the XML object.
		public function propertyIsEnumerable (P:* = null) : Boolean;

		/// Removes the given namespace for this object and all descendants.
		public function removeNamespace (ns:*) : XML;

		/// Replaces the properties specified by the propertyName parameter with the given value parameter.
		public function replace (propertyName:*, value:*) : XML;

		/// Replaces the child properties of the XML object with the specified set of XML properties, provided in the value parameter.
		public function setChildren (value:*) : XML;

		/// Changes the local name of the XML object to the given name parameter.
		public function setLocalName (name:*) : void;

		/// Sets the name of the XML object to the given qualified name or attribute name.
		public function setName (name:*) : void;

		/// Sets the namespace associated with the XML object.
		public function setNamespace (ns:*) : void;

		public function setNotification (f:Function) : *;

		/// Sets values for the following XML properties: ignoreComments, ignoreProcessingInstructions, ignoreWhitespace, prettyIndent, and prettyPrinting.
		public static function setSettings (o:Object = null) : void;

		/// Retrieves the following properties: ignoreComments, ignoreProcessingInstructions, ignoreWhitespace, prettyIndent, and prettyPrinting.
		public static function settings () : Object;

		/// Returns an XMLList object of all XML properties of the XML object that represent XML text nodes.
		public function text () : XMLList;

		/// Returns a string representation of the XML object.
		public function toString () : String;

		/// Returns a string representation of the XML object.
		public function toXMLString () : String;

		/// Returns the XML object.
		public function valueOf () : XML;

		/// Creates a new XML object.
		public function XML (value:* = null);
	}
}
