package
{
	/// The XMLList class contains methods for working with one or more XML elements.
	public class XMLList extends Object
	{
		/// Returns the number of properties in the XMLList object.
		public static const length : *;

		public function addNamespace (ns:*) : XML;

		public function appendChild (child:*) : XML;

		/// Calls the attribute() method of each XML object and returns an XMLList object of the results.
		public function attribute (arg:*) : XMLList;

		/// Calls the attributes() method of each XML object and returns an XMLList object of attributes for each XML object.
		public function attributes () : XMLList;

		/// Calls the child() method of each XML object and returns an XMLList object that contains the results in order.
		public function child (propertyName:*) : XMLList;

		public function childIndex () : int;

		/// Calls the children() method of each XML object and returns an XMLList object that contains the results.
		public function children () : XMLList;

		/// Calls the comments() method of each XML object and returns an XMLList of comments.
		public function comments () : XMLList;

		/// Checks whether the XMLList object contains an XML object that is equal to the given value parameter.
		public function contains (value:*) : Boolean;

		/// Returns a copy of the given XMLList object.
		public function copy () : XMLList;

		/// Returns all descendants (children, grandchildren, great-grandchildren, and so on) of the XML object that have the given name parameter.
		public function descendants (name:* = "*") : XMLList;

		/// Calls the elements() method of each XML object.
		public function elements (name:* = "*") : XMLList;

		/// Checks whether the XMLList object contains complex content.
		public function hasComplexContent () : Boolean;

		/// Checks for the property specified by p.
		public function hasOwnProperty (P:* = null) : Boolean;

		/// Checks whether the XMLList object contains simple content.
		public function hasSimpleContent () : Boolean;

		public function inScopeNamespaces () : Array;

		public function insertChildAfter (child1:*, child2:*) : *;

		public function insertChildBefore (child1:*, child2:*) : *;

		public function length () : int;

		public function localName () : Object;

		public function name () : Object;

		public function namespace (prefix:* = null) : *;

		public function namespaceDeclarations () : Array;

		public function nodeKind () : String;

		/// Merges adjacent text nodes and eliminates empty text nodes for each of the following: all text nodes in the XMLList, all the XML objects contained in the XMLList, and the descendants of all the XML objects in the XMLList.
		public function normalize () : XMLList;

		/// Returns the parent of the XMLList object if all items in the XMLList object have the same parent.
		public function parent () : *;

		public function prependChild (value:*) : XML;

		/// If a name parameter is provided, lists all the children of the XMLList object that contain processing instructions with that name.
		public function processingInstructions (name:* = "*") : XMLList;

		/// Checks whether the property p is in the set of properties that can be iterated in a for..in statement applied to the XMLList object.
		public function propertyIsEnumerable (P:* = null) : Boolean;

		public function removeNamespace (ns:*) : XML;

		public function replace (propertyName:*, value:*) : XML;

		public function setChildren (value:*) : XML;

		public function setLocalName (name:*) : void;

		public function setName (name:*) : void;

		public function setNamespace (ns:*) : void;

		/// Calls the text() method of each XML object and returns an XMLList object that contains the results.
		public function text () : XMLList;

		/// Returns a string representation of all the XML objects in an XMLList object.
		public function toString () : String;

		/// Returns a string representation of all the XML objects in an XMLList object.
		public function toXMLString () : String;

		/// Returns the XMLList object.
		public function valueOf () : XMLList;

		/// Creates a new XMLList object.
		public function XMLList (value:* = null);
	}
}
