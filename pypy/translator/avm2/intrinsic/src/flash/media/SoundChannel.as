package flash.media
{
	import flash.events.EventDispatcher;
	import flash.media.SoundTransform;

	/**
	 * Dispatched when a sound has finished playing.
	 * @eventType flash.events.Event.SOUND_COMPLETE
	 */
	[Event(name="soundComplete", type="flash.events.Event")] 

	/// The SoundChannel class controls a sound in an application.
	public class SoundChannel extends EventDispatcher
	{
		/// The current amplitude (volume) of the left channel, from 0 (silent) to 1 (full amplitude).
		public function get leftPeak () : Number;

		/// When the sound is playing, the position property indicates the current point that is being played in the sound file.
		public function get position () : Number;

		/// The current amplitude (volume) of the right channel, from 0 (silent) to 1 (full amplitude).
		public function get rightPeak () : Number;

		/// The SoundTransform object assigned to the sound channel.
		public function get soundTransform () : SoundTransform;
		public function set soundTransform (sndTransform:SoundTransform) : void;

		public function SoundChannel ();

		/// Stops the sound playing in the channel.
		public function stop () : void;
	}
}
