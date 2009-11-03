package flash.ui
{
	import flash.ui.ContextMenuClipboardItems;

	/// The ContextMenuClipboardItems class determines which items are enabled or disabled on the clipboard context menu.
	public class ContextMenuClipboardItems extends Object
	{
		/// Enables or disables the 'Delete' (Windows) / 'Clear' (Mac) item on the clipboard menu.
		public var clear : Boolean;
		/// Enables or disables the 'Copy' item on the clipboard menu.
		public var copy : Boolean;
		/// Enables or disables the 'Cut' item on the clipboard menu.
		public var cut : Boolean;
		/// Enables or disables the 'Paste' item on the clipboard menu.
		public var paste : Boolean;
		/// Enables or disables the 'Select All' item on the clipboard menu.
		public var selectAll : Boolean;

		public function clone () : ContextMenuClipboardItems;

		/// Creates a new ContextMenuClipboardItems object so that you can set the properties for Flash Player to enable or disable each menu item.
		public function ContextMenuClipboardItems ();
	}
}
