package flash.utils
{
	/// The Proxy class lets you override the default behavior of ActionScript operations (such as retrieving and modifying properties) on an object.
	public class Proxy extends Object
	{
		/// Overrides the behavior of an object property that can be called as a function.
		flash_proxy function callProperty (name:*, ...rest) : *;

		/// Overrides the request to delete a property.
		flash_proxy function deleteProperty (name:*) : Boolean;

		/// Overrides the use of the descendant operator.
		flash_proxy function getDescendants (name:*) : *;

		/// Overrides any request for a property's value.
		flash_proxy function getProperty (name:*) : *;

		/// Overrides a request to check whether an object has a particular property by name.
		flash_proxy function hasProperty (name:*) : Boolean;

		/// Checks whether a supplied QName is also marked as an attribute.
		flash_proxy function isAttribute (name:*) : Boolean;

		/// Allows enumeration of the proxied object's properties by index number to retrieve property names.
		flash_proxy function nextName (index:int) : String;

		/// Allows enumeration of the proxied object's properties by index number.
		flash_proxy function nextNameIndex (index:int) : int;

		/// Allows enumeration of the proxied object's properties by index number to retrieve property values.
		flash_proxy function nextValue (index:int) : *;

		flash_proxy function Proxy ();

		/// Overrides a call to change a property's value.
		flash_proxy function setProperty (name:*, value:*) : void;
	}
}
