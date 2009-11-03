package flash.media
{
	/// The SoundLoaderContext class provides security checks for SWF files that load sound.
	public class SoundLoaderContext extends Object
	{
		/// The number of milliseconds to preload a streaming sound into a buffer before the sound starts to stream.
		public var bufferTime : Number;
		/// Specifies whether Flash Player should try to download a URL policy file from the loaded sound's server before beginning to load the sound.
		public var checkPolicyFile : Boolean;

		/// Creates a new sound loader context object.
		public function SoundLoaderContext (bufferTime:Number = 1000, checkPolicyFile:Boolean = false);
	}
}
