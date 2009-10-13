package flash.display
{
	import flash.display.DisplayObject;
	import flash.text.TextSnapshot;
	import flash.geom.Point;

	/// The DisplayObjectContainer class is the base class for all objects that can serve as display object containers on the display list.
	public class DisplayObjectContainer extends InteractiveObject
	{
		/// Determines whether or not the children of the object are mouse enabled.
		public function get mouseChildren () : Boolean;
		public function set mouseChildren (enable:Boolean) : void;

		/// Returns the number of children of this object.
		public function get numChildren () : int;

		/// Determines whether the children of the object are tab enabled.
		public function get tabChildren () : Boolean;
		public function set tabChildren (enable:Boolean) : void;

		/// Returns a TextSnapshot object for this DisplayObjectContainer instance.
		public function get textSnapshot () : TextSnapshot;

		/// Adds a child object to this DisplayObjectContainer instance.
		public function addChild (child:DisplayObject) : DisplayObject;

		/// Adds a child object to this DisplayObjectContainer instance.
		public function addChildAt (child:DisplayObject, index:int) : DisplayObject;

		/// Indicates whether the security restrictions would cause any display objects to be omitted from the list returned by calling the DisplayObjectContainer.getObjectsUnderPoint() method with the specified point point.
		public function areInaccessibleObjectsUnderPoint (point:Point) : Boolean;

		/// Determines whether the specified display object is a child of the DisplayObjectContainer instance or the instance itself.
		public function contains (child:DisplayObject) : Boolean;

		/// Calling the new DisplayObjectContainer() constructor throws an ArgumentError exception.
		public function DisplayObjectContainer ();

		/// Returns the child display object instance that exists at the specified index.
		public function getChildAt (index:int) : DisplayObject;

		/// Returns the child display object that exists with the specified name.
		public function getChildByName (name:String) : DisplayObject;

		/// Returns the index number of a child DisplayObject instance.
		public function getChildIndex (child:DisplayObject) : int;

		/// Returns an array of objects that lie under the specified point and are children (or grandchildren, and so on) of this DisplayObjectContainer instance.
		public function getObjectsUnderPoint (point:Point) : Array;

		/// Removes a child display object from the DisplayObjectContainer instance.
		public function removeChild (child:DisplayObject) : DisplayObject;

		/// Removes a child display object, at the specified index position, from the DisplayObjectContainer instance.
		public function removeChildAt (index:int) : DisplayObject;

		/// Changes the index number of an existing child.
		public function setChildIndex (child:DisplayObject, index:int) : void;

		/// Swaps the z-order (front-to-back order) of the two specified child objects.
		public function swapChildren (child1:DisplayObject, child2:DisplayObject) : void;

		/// Swaps the z-order (front-to-back order) of the child objects at the two specified index positions in the child list.
		public function swapChildrenAt (index1:int, index2:int) : void;
	}
}
