package flash.display
{
	import flash.display.DisplayObject;
	import flash.media.SoundTransform;
	import flash.display.Sprite;
	import flash.display.Graphics;
	import flash.geom.Rectangle;

	/// The Sprite class is a basic display list building block: a display list node that can display graphics and can also contain children.
	public class Sprite extends DisplayObjectContainer
	{
		/// Specifies the button mode of this sprite.
		public function get buttonMode () : Boolean;
		public function set buttonMode (value:Boolean) : void;

		/// Specifies the display object over which the sprite is being dragged, or on which the sprite was dropped.
		public function get dropTarget () : DisplayObject;

		/// Specifies the Graphics object that belongs to this sprite where vector drawing commands can occur.
		public function get graphics () : Graphics;

		/// Designates another sprite to serve as the hit area for a sprite.
		public function get hitArea () : Sprite;
		public function set hitArea (value:Sprite) : void;

		/// Controls sound within this sprite.
		public function get soundTransform () : SoundTransform;
		public function set soundTransform (sndTransform:SoundTransform) : void;

		/// A Boolean value that indicates whether the pointing hand (hand cursor) appears when the mouse rolls over a sprite in which the buttonMode property is set to true.
		public function get useHandCursor () : Boolean;
		public function set useHandCursor (value:Boolean) : void;

		/// Creates a new Sprite instance.
		public function Sprite ();

		/// Lets the user drag the specified sprite.
		public function startDrag (lockCenter:Boolean = false, bounds:Rectangle = null) : void;

		/// Ends the startDrag() method.
		public function stopDrag () : void;

		public function toString () : String;
	}
}
