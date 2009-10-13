package adobe.utils
{
	/// The methods of the CustomActions class allow a SWF file playing in the Flash authoring tool to manage any custom actions that are registered with the authoring tool.
	public class CustomActions extends Object
	{
		/// Returns an Array object containing the names of all the custom actions that are registered with the Flash authoring tool.
		public static function get actionsList () : Array;

		public function CustomActions ();

		/// Reads the contents of the custom action XML definition file named name.
		public static function getActions (name:String) : String;

		/// Installs a new custom action XML definition file indicated by the name parameter.
		public static function installActions (name:String, data:String) : void;

		/// Removes the Custom Actions XML definition file named name.
		public static function uninstallActions (name:String) : void;
	}
}
