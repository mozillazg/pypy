package flash.display
{
	import flash.display.DisplayObject;
	import flash.geom.Rectangle;
	import flash.text.TextSnapshot;
	import flash.display.InteractiveObject;
	import flash.accessibility.AccessibilityImplementation;
	import flash.accessibility.AccessibilityProperties;
	import flash.events.Event;
	import flash.ui.ContextMenu;
	import flash.geom.Transform;

	/**
	 * Dispatched when the Stage object enters, or leaves, full-screen mode.
	 * @eventType flash.events.FullScreenEvent.FULL_SCREEN
	 */
	[Event(name="fullScreen", type="flash.events.FullScreenEvent")] 

	/**
	 * Dispatched when the scaleMode property of the Stage object is set to StageScaleMode.NO_SCALE and the SWF file is resized.
	 * @eventType flash.events.Event.RESIZE
	 */
	[Event(name="resize", type="flash.events.Event")] 

	/**
	 * Dispatched by the Stage object when the mouse pointer moves out of the stage area.
	 * @eventType flash.events.Event.MOUSE_LEAVE
	 */
	[Event(name="mouseLeave", type="flash.events.Event")] 

	/// The Stage class represents the main drawing area.
	public class Stage extends DisplayObjectContainer
	{
		public function set accessibilityImplementation (value:AccessibilityImplementation) : void;

		public function set accessibilityProperties (value:AccessibilityProperties) : void;

		/// A value from the StageAlign class that specifies the alignment of the stage in Flash Player or the browser.
		public function get align () : String;
		public function set align (value:String) : void;

		public function set alpha (value:Number) : void;

		public function set blendMode (value:String) : void;

		public function set cacheAsBitmap (value:Boolean) : void;

		/// Controls Flash Player color correction for displays.
		public function get colorCorrection () : String;
		public function set colorCorrection (value:String) : void;

		/// Specifies whether Flash Player is running on an operating system that supports color correction and whether the color profile of the main (primary) monitor can be read and understood by Flash Player.
		public function get colorCorrectionSupport () : String;

		public function set contextMenu (value:ContextMenu) : void;

		/// A value from the StageDisplayState class that specifies which display state to use.
		public function get displayState () : String;
		public function set displayState (value:String) : void;

		public function set filters (value:Array) : void;

		/// The interactive object with keyboard focus; or null if focus is not set or if the focused object belongs to a security sandbox to which the calling object does not have access.
		public function get focus () : InteractiveObject;
		public function set focus (newFocus:InteractiveObject) : void;

		public function set focusRect (value:Object) : void;

		/// Gets and sets the frame rate of the stage.
		public function get frameRate () : Number;
		public function set frameRate (value:Number) : void;

		/// Returns the height of the monitor that will be used when going to full screen size, if that state is entered immediately.
		public function get fullScreenHeight () : uint;

		/// Sets Flash Player to scale a specific region of the stage to full-screen mode.
		public function get fullScreenSourceRect () : Rectangle;
		public function set fullScreenSourceRect (value:Rectangle) : void;

		/// Returns the width of the monitor that will be used when going to full screen size, if that state is entered immediately.
		public function get fullScreenWidth () : uint;

		/// Indicates the height of the display object, in pixels.
		public function get height () : Number;
		public function set height (value:Number) : void;

		public function set mask (value:DisplayObject) : void;

		/// Determines whether or not the children of the object are mouse enabled.
		public function get mouseChildren () : Boolean;
		public function set mouseChildren (value:Boolean) : void;

		public function set mouseEnabled (value:Boolean) : void;

		public function set name (value:String) : void;

		/// Returns the number of children of this object.
		public function get numChildren () : int;

		public function set opaqueBackground (value:Object) : void;

		/// A value from the StageQuality class that specifies which rendering quality is used.
		public function get quality () : String;
		public function set quality (value:String) : void;

		public function set rotation (value:Number) : void;

		public function set rotationX (value:Number) : void;

		public function set rotationY (value:Number) : void;

		public function set rotationZ (value:Number) : void;

		public function set scale9Grid (value:Rectangle) : void;

		/// A value from the StageScaleMode class that specifies which scale mode to use.
		public function get scaleMode () : String;
		public function set scaleMode (value:String) : void;

		public function set scaleX (value:Number) : void;

		public function set scaleY (value:Number) : void;

		public function set scaleZ (value:Number) : void;

		public function set scrollRect (value:Rectangle) : void;

		/// Specifies whether to show or hide the default items in the Flash Player context menu.
		public function get showDefaultContextMenu () : Boolean;
		public function set showDefaultContextMenu (value:Boolean) : void;

		/// Specifies whether or not objects display a glowing border when they have focus.
		public function get stageFocusRect () : Boolean;
		public function set stageFocusRect (on:Boolean) : void;

		/// The current height, in pixels, of the Stage.
		public function get stageHeight () : int;
		public function set stageHeight (value:int) : void;

		/// Specifies the current width, in pixels, of the Stage.
		public function get stageWidth () : int;
		public function set stageWidth (value:int) : void;

		/// Determines whether the children of the object are tab enabled.
		public function get tabChildren () : Boolean;
		public function set tabChildren (value:Boolean) : void;

		public function set tabEnabled (value:Boolean) : void;

		public function set tabIndex (value:int) : void;

		/// Returns a TextSnapshot object for this DisplayObjectContainer instance.
		public function get textSnapshot () : TextSnapshot;

		public function set transform (value:Transform) : void;

		/// Indicates the width of the display object, in pixels.
		public function get width () : Number;
		public function set width (value:Number) : void;

		public function set visible (value:Boolean) : void;

		public function set x (value:Number) : void;

		public function set y (value:Number) : void;

		public function set z (value:Number) : void;

		/// Adds a child DisplayObject instance to this DisplayObjectContainer instance.
		public function addChild (child:DisplayObject) : DisplayObject;

		/// Adds a child DisplayObject instance to this DisplayObjectContainer instance.
		public function addChildAt (child:DisplayObject, index:int) : DisplayObject;

		/// Registers an event listener object with an EventDispatcher object so that the listener receives notification of an event.
		public function addEventListener (type:String, listener:Function, useCapture:Boolean = false, priority:int = 0, useWeakReference:Boolean = false) : void;

		/// Dispatches an event into the event flow.
		public function dispatchEvent (event:Event) : Boolean;

		/// Checks whether the EventDispatcher object has any listeners registered for a specific type of event.
		public function hasEventListener (type:String) : Boolean;

		/// Signals Flash Player to update properties of display objects on the next opportunity it has to refresh the Stage.
		public function invalidate () : void;

		/// Determines whether the Stage.focus property would return null for security reasons.
		public function isFocusInaccessible () : Boolean;

		/// Removes a child DisplayObject from the specified index position in the child list of the DisplayObjectContainer.
		public function removeChildAt (index:int) : DisplayObject;

		/// Changes the position of an existing child in the display object container.
		public function setChildIndex (child:DisplayObject, index:int) : void;

		public function Stage ();

		/// Swaps the z-order (front-to-back order) of the child objects at the two specified index positions in the child list.
		public function swapChildrenAt (index1:int, index2:int) : void;

		/// Checks whether an event listener is registered with this EventDispatcher object or any of its ancestors for the specified event type.
		public function willTrigger (type:String) : Boolean;
	}
}
