package flash.display
{
	import flash.display.DisplayObject;
	import flash.media.SoundTransform;

	/// The SimpleButton class lets you control all instances of button symbols in a SWF file.
	public class SimpleButton extends InteractiveObject
	{
		/// Specifies a display object that is used as the visual object for the button "Down" state - the state that the button is in when the user clicks the hitTestState object.
		public function get downState () : DisplayObject;
		public function set downState (value:DisplayObject) : void;

		/// A Boolean value that specifies whether a button is enabled.
		public function get enabled () : Boolean;
		public function set enabled (value:Boolean) : void;

		/// Specifies a display object that is used as the hit testing object for the button.
		public function get hitTestState () : DisplayObject;
		public function set hitTestState (value:DisplayObject) : void;

		/// Specifies a display object that is used as the visual object for the button over state - the state that the button is in when the mouse is positioned over the button.
		public function get overState () : DisplayObject;
		public function set overState (value:DisplayObject) : void;

		/// The SoundTransform object assigned to this button.
		public function get soundTransform () : SoundTransform;
		public function set soundTransform (sndTransform:SoundTransform) : void;

		/// Indicates whether other display objects that are SimpleButton or MovieClip objects can receive mouse release events.
		public function get trackAsMenu () : Boolean;
		public function set trackAsMenu (value:Boolean) : void;

		/// Specifies a display object that is used as the visual object for the button up state - the state that the button is in when the mouse is not positioned over the button.
		public function get upState () : DisplayObject;
		public function set upState (value:DisplayObject) : void;

		/// A Boolean value that, when set to true, indicates whether Flash Player displays the hand cursor when the mouse rolls over a button.
		public function get useHandCursor () : Boolean;
		public function set useHandCursor (value:Boolean) : void;

		/// Creates a new SimpleButton instance.
		public function SimpleButton (upState:DisplayObject = null, overState:DisplayObject = null, downState:DisplayObject = null, hitTestState:DisplayObject = null);
	}
}
