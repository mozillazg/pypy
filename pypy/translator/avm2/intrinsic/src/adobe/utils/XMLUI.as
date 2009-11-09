package adobe.utils
{
	/// The XMLUI class enables communication with SWF files that are used as custom user interfaces for the Flash authoring tool's extensibility features.
	public class XMLUI extends Object
	{
		/// Makes the current XMLUI dialog box close with an "accept" state.
		public static function accept () : void;

		/// Makes the current XMLUI dialog box close with a "cancel" state.
		public static function cancel () : void;

		/// Retrieves the value of the specified property of the current XMLUI dialog box.
		public static function getProperty (name:String) : String;

		/// Modifies the value of the specified property of the current XMLUI dialog.
		public static function setProperty (name:String, value:String) : void;

		public function XMLUI ();
	}
}
