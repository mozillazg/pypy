package flash.system
{
	/// The SecurityPanel class provides values for specifying which Security Settings panel you want to display.
	public class SecurityPanel extends Object
	{
		/// When passed to Security.showSettings(), displays the Camera panel in Flash Player Settings.
		public static const CAMERA : String;
		/// When passed to Security.showSettings(), displays the panel that was open the last time the user closed the Flash Player Settings.
		public static const DEFAULT : String;
		/// When passed to Security.showSettings(), displays the Display panel in Flash Player Settings.
		public static const DISPLAY : String;
		/// When passed to Security.showSettings(), displays the Local Storage Settings panel in Flash Player Settings.
		public static const LOCAL_STORAGE : String;
		/// When passed to Security.showSettings(), displays the Microphone panel in Flash Player Settings.
		public static const MICROPHONE : String;
		/// When passed to Security.showSettings(), displays the Privacy Settings panel in Flash Player Settings.
		public static const PRIVACY : String;
		/// When passed to Security.showSettings(), displays the Settings Manager (in a separate browser window).
		public static const SETTINGS_MANAGER : String;

		public function SecurityPanel ();
	}
}
