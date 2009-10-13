package
{
	/// The Object class is at the root of the ActionScript class hierarchy.
	public class Object extends *
	{
		/// Indicates whether an object has a specified property defined.
		public function hasOwnProperty (V:* = null) : Boolean;

		/// Indicates whether an instance of the Object class is in the prototype chain of the object specified as the parameter.
		public function isPrototypeOf (V:* = null) : Boolean;

		/// Creates an Object object and stores a reference to the object's constructor method in the object's constructor property.
		public function Object ();

		/// Indicates whether the specified property exists and is enumerable.
		public function propertyIsEnumerable (V:* = null) : Boolean;

		public function toString () : String;

		public function valueOf () : Object;

		public function setPropertyIsEnumerable (name:String, isEnum:Boolean = true) : void;
	}
}
