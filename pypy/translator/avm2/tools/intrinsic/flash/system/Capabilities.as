package flash.system
{
	/// The Capabilities class provides properties that describe the system and player that are hosting a SWF file.
	public class Capabilities extends Object
	{
		public static function get _internal () : uint;

		/// Specifies whether access to the user's camera and microphone has been administratively prohibited (true) or allowed (false).
		public static function get avHardwareDisable () : Boolean;

		/// Specifies whether the system supports (true) or does not support (false) communication with accessibility aids.
		public static function get hasAccessibility () : Boolean;

		/// Specifies whether the system has audio capabilities.
		public static function get hasAudio () : Boolean;

		/// Specifies whether the system can (true) or cannot (false) encode an audio stream, such as that coming from a microphone.
		public static function get hasAudioEncoder () : Boolean;

		/// Specifies whether the system supports (true) or does not support (false) embedded video.
		public static function get hasEmbeddedVideo () : Boolean;

		/// Specifies whether the system does (true) or does not (false) have an input method editor (IME) installed.
		public static function get hasIME () : Boolean;

		/// Specifies whether the system does (true) or does not (false) have an MP3 decoder.
		public static function get hasMP3 () : Boolean;

		/// Specifies whether the system does (true) or does not (false) support printing.
		public static function get hasPrinting () : Boolean;

		/// Specifies whether the system does (true) or does not (false) support the development of screen broadcast applications to be run through Flash Media Server.
		public static function get hasScreenBroadcast () : Boolean;

		/// Specifies whether the system does (true) or does not (false) support the playback of screen broadcast applications that are being run through Flash Media Server.
		public static function get hasScreenPlayback () : Boolean;

		/// Specifies whether the system can (true) or cannot (false) play streaming audio.
		public static function get hasStreamingAudio () : Boolean;

		/// Specifies whether the system can (true) or cannot (false) play streaming video.
		public static function get hasStreamingVideo () : Boolean;

		/// Specifies whether the system supports native SSL sockets through NetConnection (true) or does not (false).
		public static function get hasTLS () : Boolean;

		/// Specifies whether the system can (true) or cannot (false) encode a video stream, such as that coming from a web camera.
		public static function get hasVideoEncoder () : Boolean;

		/// Specifies whether the system is using special debugging software (true) or an officially released version (false).
		public static function get isDebugger () : Boolean;

		/// Specifies the language code of the system on which the content is running.
		public static function get language () : String;

		/// Specifies whether read access to the user's hard disk has been administratively prohibited (true) or allowed (false).
		public static function get localFileReadDisable () : Boolean;

		/// Specifies the manufacturer of the running version of Flash Player or  the AIR runtime, in the format "Adobe <em>OSName".
		public static function get manufacturer () : String;

		/// Retrieves the highest H.264 Level IDC that the client hardware supports.
		public static function get maxLevelIDC () : String;

		/// Specifies the current operating system.
		public static function get os () : String;

		/// Specifies the pixel aspect ratio of the screen.
		public static function get pixelAspectRatio () : Number;

		/// Specifies the type of runtime environment.
		public static function get playerType () : String;

		/// Specifies the screen color.
		public static function get screenColor () : String;

		/// Specifies the dots-per-inch (dpi) resolution of the screen, in pixels.
		public static function get screenDPI () : Number;

		/// Specifies the maximum horizontal resolution of the screen.
		public static function get screenResolutionX () : Number;

		/// Specifies the maximum vertical resolution of the screen.
		public static function get screenResolutionY () : Number;

		/// A URL-encoded string that specifies values for each Capabilities property.
		public static function get serverString () : String;

		/// Specifies the Flash Player or Adobe AIR platform and version information.
		public static function get version () : String;

		public function Capabilities ();
	}
}
