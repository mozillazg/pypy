package flash.media
{
	import flash.events.EventDispatcher;
	import flash.media.Microphone;
	import flash.media.SoundTransform;

	/**
	 * Dispatched when a microphone reports its status.
	 * @eventType flash.events.StatusEvent.STATUS
	 */
	[Event(name="status", type="flash.events.StatusEvent")] 

	/**
	 * Dispatched when a microphone begins or ends a session.
	 * @eventType flash.events.ActivityEvent.ACTIVITY
	 */
	[Event(name="activity", type="flash.events.ActivityEvent")] 

	/// Use the Microphone class to capture audio from a microphone attached to a computer running Flash Player.
	public class Microphone extends EventDispatcher
	{
		/// The amount of sound the microphone is detecting.
		public function get activityLevel () : Number;

		/// The codec to use for compressing audio.
		public function get codec () : String;
		public function set codec (codec:String) : void;

		/// The encoded speech quality when using the Speex codec.
		public function get encodeQuality () : int;
		public function set encodeQuality (quality:int) : void;

		/// Number of Speex speech frames transmitted in a packet (message).
		public function get framesPerPacket () : int;
		public function set framesPerPacket (frames:int) : void;

		/// The microphone gain--that is, the amount by which the microphone multiplies the signal before transmitting it.
		public function get gain () : Number;
		public function set gain (gain:Number) : void;

		/// The index of the microphone, as reflected in the array returned by Microphone.names.
		public function get index () : int;

		/// Specifies whether the user has denied access to the microphone (true) or allowed access (false).
		public function get muted () : Boolean;

		/// The name of the current sound capture device, as returned by the sound capture hardware.
		public function get name () : String;

		/// An array of strings containing the names of all available sound capture devices.
		public static function get names () : Array;

		/// The rate at which the microphone captures sound, in kHz.
		public function get rate () : int;
		public function set rate (rate:int) : void;

		/// The amount of sound required to activate the microphone and dispatch the activity event.
		public function get silenceLevel () : Number;

		/// The number of milliseconds between the time the microphone stops detecting sound and the time the activity event is dispatched.
		public function get silenceTimeout () : int;

		/// Controls the sound of this microphone object when it is in loopback mode.
		public function get soundTransform () : SoundTransform;
		public function set soundTransform (sndTransform:SoundTransform) : void;

		/// Set to true if echo suppression is enabled; false otherwise.
		public function get useEchoSuppression () : Boolean;

		/// Returns a reference to a Microphone object for capturing audio.
		public static function getMicrophone (index:int = -1) : Microphone;

		public function Microphone ();

		/// Routes audio captured by a microphone to the local speakers.
		public function setLoopBack (state:Boolean = true) : void;

		/// Sets the minimum input level that should be considered sound and (optionally) the amount of silent time signifying that silence has actually begun.
		public function setSilenceLevel (silenceLevel:Number, timeout:int = -1) : void;

		/// Specifies whether to use the echo suppression feature of the audio codec.
		public function setUseEchoSuppression (useEchoSuppression:Boolean) : void;
	}
}
