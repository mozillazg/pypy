package flash.system
{
	/// The Security class lets you specify how content in different domains can communicate with each other.
	public class Security extends Object
	{
		/// The file is a local file and has been trusted by the user, using either the Flash Player Settings Manager or a FlashPlayerTrust configuration file.
		public static const LOCAL_TRUSTED : String;
		/// The file is a local file, has not been trusted by the user, and it is not a SWF file that was published with a networking designation.
		public static const LOCAL_WITH_FILE : String;
		/// The file is a local file, has not been trusted by the user, and it is a SWF file that was published with a networking designation.
		public static const LOCAL_WITH_NETWORK : String;
		/// The file is from an Internet URL and operates under domain-based sandbox rules.
		public static const REMOTE : String;

		public static function get disableAVM1Loading () : Boolean;
		public static function set disableAVM1Loading (value:Boolean) : void;

		/// Determines how Flash Player or AIR chooses the domain to use for certain content settings, including settings for camera and microphone permissions, storage quotas, and storage of persistent shared objects.
		public static function get exactSettings () : Boolean;
		public static function set exactSettings (value:Boolean) : void;

		/// Indicates the type of security sandbox in which the calling file is operating.
		public static function get sandboxType () : String;

		/// Lets SWF files and HTML files access objects and variables in the calling SWF file.
		public static function allowDomain (...rest) : void;

		/// Lets SWF and HTML files hosted using the HTTPS protocol, access objects and variables in the calling SWF file.
		public static function allowInsecureDomain (...rest) : void;

		/// Loads a URL policy file from a location specified by the url parameter.
		public static function loadPolicyFile (url:String) : void;

		public function Security ();

		/// Displays the Security Settings panel in Flash Player.
		public static function showSettings (panel:String = "default") : void;
	}
}
