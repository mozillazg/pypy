package flash.media
{
	import flash.media.SoundTransform;
	import flash.utils.ByteArray;

	/// The SoundMixer class contains static properties and methods for global sound controlin the SWF file.
	public class SoundMixer extends Object
	{
		/// The number of seconds to preload an embedded streaming sound into a buffer before it starts to stream.
		public static function get bufferTime () : int;
		public static function set bufferTime (bufferTime:int) : void;

		/// The SoundTransform object that controls global sound properties.
		public static function get soundTransform () : SoundTransform;
		public static function set soundTransform (sndTransform:SoundTransform) : void;

		/// Determines whether any sounds are not accessible due to security restrictions.
		public static function areSoundsInaccessible () : Boolean;

		/// Takes a snapshot of the current sound wave and places it into the specified ByteArray object.
		public static function computeSpectrum (outputArray:ByteArray, FFTMode:Boolean = false, stretchFactor:int = 0) : void;

		public function SoundMixer ();

		/// Stops all sounds currently playing.
		public static function stopAll () : void;
	}
}
