package flash.external
{
	/// The ExternalInterface class is the External API, an application programming interface that enables straightforward communication between ActionScript and the Flash Player container - for example, an HTML page with JavaScript.
	public class ExternalInterface extends Object
	{
		/// Indicates whether the external interface should attempt to pass ActionScript exceptions to the current browser and JavaScript exceptions to Flash Player.
		public static var marshallExceptions : Boolean;

		/// Indicates whether this player is in a container that offers an external interface.
		public static function get available () : Boolean;

		/// Returns the id attribute of the object tag in Internet Explorer, or the name attribute of the embed tag in Netscape.
		public static function get objectID () : String;

		/// Registers an ActionScript method as callable from the container.
		public static function addCallback (functionName:String, closure:Function) : void;

		/// Calls a function in the container.
		public static function call (functionName:String, ...rest) : *;

		public function ExternalInterface ();
	}
}
