package flash.display
{
	import flash.events.EventDispatcher;
	import flash.display.IBitmapDrawable;
	import flash.display.DisplayObject;
	import flash.geom.Point;
	import flash.geom.Rectangle;
	import flash.accessibility.AccessibilityProperties;
	import flash.display.Shader;
	import flash.display.DisplayObjectContainer;
	import flash.geom.Vector3D;
	import flash.geom.Transform;
	import flash.display.LoaderInfo;
	import flash.display.Stage;

	/**
	 * [broadcast event] Dispatched when the display list is about to be updated and rendered.
	 * @eventType flash.events.Event.RENDER
	 */
	[Event(name="render", type="flash.events.Event")] 

	/**
	 * Dispatched when a display object is about to be removed from the display list, either directly or through the removal of a sub tree in which the display object is contained.
	 * @eventType flash.events.Event.REMOVED_FROM_STAGE
	 */
	[Event(name="removedFromStage", type="flash.events.Event")] 

	/**
	 * Dispatched when a display object is about to be removed from the display list.
	 * @eventType flash.events.Event.REMOVED
	 */
	[Event(name="removed", type="flash.events.Event")] 

	/**
	 * [broadcast event] Dispatched when the playhead is exiting the current frame.
	 * @eventType flash.events.Event.EXIT_FRAME
	 */
	[Event(name="exitFrame", type="flash.events.Event")] 

	/**
	 * [broadcast event] Dispatched after the constructors of frame display objects have run but before frame scripts have run.
	 * @eventType flash.events.Event.FRAME_CONSTRUCTED
	 */
	[Event(name="frameConstructed", type="flash.events.Event")] 

	/**
	 * [broadcast event] Dispatched when the playhead is entering a new frame.
	 * @eventType flash.events.Event.ENTER_FRAME
	 */
	[Event(name="enterFrame", type="flash.events.Event")] 

	/**
	 * Dispatched when a display object is added to the on stage display list, either directly or through the addition of a sub tree in which the display object is contained.
	 * @eventType flash.events.Event.ADDED_TO_STAGE
	 */
	[Event(name="addedToStage", type="flash.events.Event")] 

	/**
	 * Dispatched when a display object is added to the display list.
	 * @eventType flash.events.Event.ADDED
	 */
	[Event(name="added", type="flash.events.Event")] 

	/// The DisplayObject class is the base class for all objects that can be placed on the display list.
	public class DisplayObject extends EventDispatcher implements IBitmapDrawable
	{
		/// The current accessibility options for this display object.
		public function get accessibilityProperties () : AccessibilityProperties;
		public function set accessibilityProperties (value:AccessibilityProperties) : void;

		/// Indicates the alpha transparency value of the object specified.
		public function get alpha () : Number;
		public function set alpha (value:Number) : void;

		/// A value from the BlendMode class that specifies which blend mode to use.
		public function get blendMode () : String;
		public function set blendMode (value:String) : void;

		/// Sets a shader that is used for blending the foreground and background.
		public function set blendShader (value:Shader) : void;

		/// If set to true, Flash Player caches an internal bitmap representation of the display object.
		public function get cacheAsBitmap () : Boolean;
		public function set cacheAsBitmap (value:Boolean) : void;

		/// An indexed array that contains each filter object currently associated with the display object.
		public function get filters () : Array;
		public function set filters (value:Array) : void;

		/// Indicates the height of the display object, in pixels.
		public function get height () : Number;
		public function set height (value:Number) : void;

		/// Returns a LoaderInfo object containing information about loading the file to which this display object belongs.
		public function get loaderInfo () : LoaderInfo;

		/// The calling display object is masked by the specified mask object.
		public function get mask () : DisplayObject;
		public function set mask (value:DisplayObject) : void;

		/// Indicates the x coordinate of the mouse position, in pixels.
		public function get mouseX () : Number;

		/// Indicates the y coordinate of the mouse position, in pixels.
		public function get mouseY () : Number;

		/// Indicates the instance name of the DisplayObject.
		public function get name () : String;
		public function set name (value:String) : void;

		/// Specifies whether the display object is opaque with a certain background color.
		public function get opaqueBackground () : Object;
		public function set opaqueBackground (value:Object) : void;

		/// Indicates the DisplayObjectContainer object that contains this display object.
		public function get parent () : DisplayObjectContainer;

		/// For a display object in a loaded SWF file, the root property is the top-most display object in the portion of the display list's tree structure represented by that SWF file.
		public function get root () : DisplayObject;

		/// Indicates the rotation of the DisplayObject instance, in degrees, from its original orientation.
		public function get rotation () : Number;
		public function set rotation (value:Number) : void;

		/// Indicates the x-axis rotation of the DisplayObject instance, in degrees, from its original orientation relative to the 3D parent container.
		public function get rotationX () : Number;
		public function set rotationX (value:Number) : void;

		/// Indicates the y-axis rotation of the DisplayObject instance, in degrees, from its original orientation relative to the 3D parent container.
		public function get rotationY () : Number;
		public function set rotationY (value:Number) : void;

		/// Indicates the z-axis rotation of the DisplayObject instance, in degrees, from its original orientation relative to the 3D parent container.
		public function get rotationZ () : Number;
		public function set rotationZ (value:Number) : void;

		/// The current scaling grid that is in effect.
		public function get scale9Grid () : Rectangle;
		public function set scale9Grid (innerRectangle:Rectangle) : void;

		/// Indicates the horizontal scale (percentage) of the object as applied from the registration point.
		public function get scaleX () : Number;
		public function set scaleX (value:Number) : void;

		/// Indicates the vertical scale (percentage) of an object as applied from the registration point of the object.
		public function get scaleY () : Number;
		public function set scaleY (value:Number) : void;

		/// Indicates the depth scale (percentage) of an object as applied from the registration point of the object.
		public function get scaleZ () : Number;
		public function set scaleZ (value:Number) : void;

		/// The scroll rectangle bounds of the display object.
		public function get scrollRect () : Rectangle;
		public function set scrollRect (value:Rectangle) : void;

		/// The Stage of the display object.
		public function get stage () : Stage;

		/// An object with properties pertaining to a display object's matrix, color transform, and pixel bounds.
		public function get transform () : Transform;
		public function set transform (value:Transform) : void;

		/// Indicates the width of the display object, in pixels.
		public function get width () : Number;
		public function set width (value:Number) : void;

		/// Whether or not the display object is visible.
		public function get visible () : Boolean;
		public function set visible (value:Boolean) : void;

		/// Indicates the x coordinate of the DisplayObject instance relative to the local coordinates of the parent DisplayObjectContainer.
		public function get x () : Number;
		public function set x (value:Number) : void;

		/// Indicates the y coordinate of the DisplayObject instance relative to the local coordinates of the parent DisplayObjectContainer.
		public function get y () : Number;
		public function set y (value:Number) : void;

		/// Indicates the z coordinate position along the z-axis of the DisplayObject instance relative to the 3D parent container.
		public function get z () : Number;
		public function set z (value:Number) : void;

		public function DisplayObject ();

		/// Returns a rectangle that defines the area of the display object relative to the coordinate system of the targetCoordinateSpace object.
		public function getBounds (targetCoordinateSpace:DisplayObject) : Rectangle;

		/// Returns a rectangle that defines the boundary of the display object, based on the coordinate system defined by the targetCoordinateSpace parameter, excluding any strokes on shapes.
		public function getRect (targetCoordinateSpace:DisplayObject) : Rectangle;

		/// Converts the point object from Stage (global) coordinates to the display object's (local) coordinates.
		public function globalToLocal (point:Point) : Point;

		/// Converts a two-dimensional point from the Stage (global) coordinates to a three-dimensional display object's (local) coordinates.
		public function globalToLocal3D (point:Point) : Vector3D;

		/// Evaluates the display object to see if it overlaps or intersects with the display object passed as a parameter.
		public function hitTestObject (obj:DisplayObject) : Boolean;

		/// Evaluates the display object to see if it overlaps or intersects with a point specified by x and y.
		public function hitTestPoint (x:Number, y:Number, shapeFlag:Boolean = false) : Boolean;

		/// Converts a three-dimensional point of the three-dimensional display object's (local) coordinates to a two-dimensional point in the Stage (global) coordinates.
		public function local3DToGlobal (point3d:Vector3D) : Point;

		/// Converts the point object from the display object's (local) coordinates to the Stage (global) coordinates.
		public function localToGlobal (point:Point) : Point;
	}
}
