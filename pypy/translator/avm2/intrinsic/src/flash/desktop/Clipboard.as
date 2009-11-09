package flash.desktop
{
	import flash.utils.Dictionary;
	import flash.desktop.Clipboard;
	import flash.utils.ByteArray;

	/// The Clipboard class provides a container for transferring data and objects through the clipboard and through drag-and-drop operations (AIR only).
	public class Clipboard extends Object
	{
		/// An array of strings containing the names of the data formats available in this Clipboard object.
		public function get formats () : Array;

		/// The operating system clipboard.
		public static function get generalClipboard () : Clipboard;

		/// Deletes all data representations from this Clipboard object.
		public function clear () : void;

		/// Deletes the data representation for the specified format.
		public function clearData (format:String) : void;

		/// Creates an empty Clipboard object.
		public function Clipboard ();

		/// Gets the clipboard data if data in the specified format is present.
		public function getData (format:String, transferMode:String = "originalPreferred") : Object;

		/// Checks whether data in the specified format exists in this Clipboard object.
		public function hasFormat (format:String) : Boolean;

		/// Adds a representation of the information to be transferred in the specified data format.
		public function setData (format:String, data:Object, serializable:Boolean = true) : Boolean;

		/// Adds a reference to a handler function that produces the data for the specified format on demand.
		public function setDataHandler (format:String, handler:Function, serializable:Boolean = true) : Boolean;
	}
}
