package flash.system
{
	import flash.system.IME;

	/// The System class contains properties related to certain operations that take place on the user's computer, such as operations with shared objects, local settings for cameras and microphones, and use of the Clipboard.
	public class System extends Object
	{
		/// The currently installed system IME.
		public static function get ime () : IME;

		/// The amount of memory (in bytes) currently in use by Adobe Flash Player.
		public static function get totalMemory () : uint;

		/// A Boolean value that tells Flash Player which code page to use to interpret external text files.
		public static function get useCodePage () : Boolean;
		public static function set useCodePage (value:Boolean) : void;

		public static function get vmVersion () : String;

		/// Closes the Flash Player.
		public static function exit (code:uint) : void;

		/// Forces the garbage collection process.
		public static function gc () : void;

		/// Pauses the Flash Player.
		public static function pause () : void;

		/// Resumes the Flash Player after using System.pause().
		public static function resume () : void;

		/// Replaces the contents of the Clipboard with a specified text string.
		public static function setClipboard (string:String) : void;

		public function System ();
	}
}
