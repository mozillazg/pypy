package flash.media
{
	import flash.display.DisplayObject;
	import flash.media.Camera;
	import flash.net.NetStream;

	/// The Video class displays live or recorded video in an application without embedding the video in your SWF file.
	public class Video extends DisplayObject
	{
		/// Indicates the type of filter applied to decoded video as part of post-processing.
		public function get deblocking () : int;
		public function set deblocking (value:int) : void;

		/// Specifies whether the video should be smoothed (interpolated) when it is scaled.
		public function get smoothing () : Boolean;
		public function set smoothing (value:Boolean) : void;

		/// An integer specifying the height of the video stream, in pixels.
		public function get videoHeight () : int;

		/// An integer specifying the width of the video stream, in pixels.
		public function get videoWidth () : int;

		/// Specifies a video stream from a camera to be displayed within the boundaries of the Video object in the application.
		public function attachCamera (camera:Camera) : void;

		/// Specifies a video stream to be displayed within the boundaries of the Video object in the application.
		public function attachNetStream (netStream:NetStream) : void;

		/// Clears the image currently displayed in the Video object (not the video stream).
		public function clear () : void;

		/// Creates a new Video instance.
		public function Video (width:int = 320, height:int = 240);
	}
}
