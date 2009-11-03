package flash.media
{
	import flash.events.EventDispatcher;
	import flash.media.Camera;

	/**
	 * Dispatched when a camera reports its status.
	 * @eventType flash.events.StatusEvent.STATUS
	 */
	[Event(name="status", type="flash.events.StatusEvent")] 

	/**
	 * Dispatched when a camera begins or ends a session.
	 * @eventType flash.events.ActivityEvent.ACTIVITY
	 */
	[Event(name="activity", type="flash.events.ActivityEvent")] 

	/// Use the Camera class to capture video from a camera attached to a computer running Flash Player.
	public class Camera extends EventDispatcher
	{
		/// The amount of motion the camera is detecting.
		public function get activityLevel () : Number;

		/// The maximum amount of bandwidth the current outgoing video feed can use, in bytes.
		public function get bandwidth () : int;

		/// The rate at which the camera is capturing data, in frames per second.
		public function get currentFPS () : Number;

		/// The maximum rate at which the camera can capture data, in frames per second.
		public function get fps () : Number;

		/// The current capture height, in pixels.
		public function get height () : int;

		/// A zero-based integer that specifies the index of the camera, as reflected in the array returned by the names property.
		public function get index () : int;

		/// The number of video frames transmitted in full (called keyframes) instead of being interpolated by the video compression algorithm.
		public function get keyFrameInterval () : int;

		/// Indicates whether a local view of what the camera is capturing is compressed and decompressed (true), as it would be for live transmission using Flash Media Server, or uncompressed (false).
		public function get loopback () : Boolean;

		/// The amount of motion required to invoke the activity event.
		public function get motionLevel () : int;

		/// The number of milliseconds between the time the camera stops detecting motion and the time the activity event is invoked.
		public function get motionTimeout () : int;

		/// A Boolean value indicating whether the user has denied access to the camera (true) or allowed access (false) in the Flash Player Privacy dialog box.
		public function get muted () : Boolean;

		/// The name of the current camera, as returned by the camera hardware.
		public function get name () : String;

		/// An array of strings indicating the names of all available cameras without displaying the Flash Player Privacy dialog box.
		public static function get names () : Array;

		/// The required level of picture quality, as determined by the amount of compression being applied to each video frame.
		public function get quality () : int;

		/// The current capture width, in pixels.
		public function get width () : int;

		public function Camera ();

		/// Returns a reference to a Camera object for capturing video.
		public static function getCamera (name:String = null) : Camera;

		public function setCursor (value:Boolean) : void;

		/// Specifies which video frames are transmitted in full (called keyframes) instead of being interpolated by the video compression algorithm.
		public function setKeyFrameInterval (keyFrameInterval:int) : void;

		/// Specifies whether to use a compressed video stream for a local view of the camera.
		public function setLoopback (compress:Boolean = false) : void;

		/// Sets the camera capture mode to the native mode that best meets the specified requirements.
		public function setMode (width:int, height:int, fps:Number, favorArea:Boolean = true) : void;

		/// Specifies how much motion is required to dispatch the activity event.
		public function setMotionLevel (motionLevel:int, timeout:int = 2000) : void;

		/// Sets the maximum amount of bandwidth per second or the required picture quality of the current outgoing video feed.
		public function setQuality (bandwidth:int, quality:int) : void;
	}
}
