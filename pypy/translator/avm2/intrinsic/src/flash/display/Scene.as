package flash.display
{
	/// The Scene class includes properties for identifying the name, labels, and number of frames in a scene.
	public class Scene extends Object
	{
		/// An array of FrameLabel objects for the scene.
		public function get labels () : Array;

		/// The name of the scene.
		public function get name () : String;

		/// The number of frames in the scene.
		public function get numFrames () : int;

		public function Scene (name:String, labels:Array, numFrames:int);
	}
}
