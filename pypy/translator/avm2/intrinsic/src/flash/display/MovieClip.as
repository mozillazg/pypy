package flash.display
{
	import flash.display.Scene;

	/// The MovieClip class inherits from the following classes: Sprite, DisplayObjectContainer, InteractiveObject, DisplayObject, and EventDispatcher.
	public class MovieClip extends Sprite
	{
		/// Specifies the number of the frame in which the playhead is located in the timeline of the MovieClip instance.
		public function get currentFrame () : int;

		/// The label at the current frame in the timeline of the MovieClip instance.
		public function get currentFrameLabel () : String;

		/// The current label in which the playhead is located in the timeline of the MovieClip instance.
		public function get currentLabel () : String;

		/// Returns an array of FrameLabel objects from the current scene.
		public function get currentLabels () : Array;

		/// The current scene in which the playhead is located in the timeline of the MovieClip instance.
		public function get currentScene () : Scene;

		/// A Boolean value that indicates whether a movie clip is enabled.
		public function get enabled () : Boolean;
		public function set enabled (value:Boolean) : void;

		/// The number of frames that are loaded from a streaming SWF file.
		public function get framesLoaded () : int;

		/// An array of Scene objects, each listing the name, the number of frames, and the frame labels for a scene in the MovieClip instance.
		public function get scenes () : Array;

		/// The total number of frames in the MovieClip instance.
		public function get totalFrames () : int;

		/// Indicates whether other display objects that are SimpleButton or MovieClip objects can receive mouse release events.
		public function get trackAsMenu () : Boolean;
		public function set trackAsMenu (value:Boolean) : void;

		/// [Undocumented] Takes a collection of frame (zero-based) - method pairs that associates a method with a frame on the timeline.
		public function addFrameScript (frame:int, method:Function) : void;

		/// Starts playing the SWF file at the specified frame.
		public function gotoAndPlay (frame:Object, scene:String = null) : void;

		/// Brings the playhead to the specified frame of the movie clip and stops it there.
		public function gotoAndStop (frame:Object, scene:String = null) : void;

		/// Creates a new MovieClip instance.
		public function MovieClip ();

		/// Sends the playhead to the next frame and stops it.
		public function nextFrame () : void;

		/// Moves the playhead to the next scene of the MovieClip instance.
		public function nextScene () : void;

		/// Moves the playhead in the timeline of the movie clip.
		public function play () : void;

		/// Sends the playhead to the previous frame and stops it.
		public function prevFrame () : void;

		/// Moves the playhead to the previous scene of the MovieClip instance.
		public function prevScene () : void;

		/// Stops the playhead in the movie clip.
		public function stop () : void;
	}
}
