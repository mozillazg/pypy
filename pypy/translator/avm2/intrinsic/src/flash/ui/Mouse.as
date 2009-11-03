package flash.ui
{
	/// The methods of the Mouse class are used to hide and show the mouse pointer, or to set the pointer to a specific style.
	public class Mouse extends Object
	{
		/// Sets the mouse cursor.
		public static function get cursor () : String;
		public static function set cursor (value:String) : void;

		/// Hides the pointer.
		public static function hide () : void;

		public function Mouse ();

		/// Displays the pointer.
		public static function show () : void;
	}
}
