package flash.ui
{
	import flash.events.EventDispatcher;
	import flash.ui.ContextMenuBuiltInItems;
	import flash.ui.ContextMenu;
	import flash.ui.ContextMenuClipboardItems;
	import flash.net.URLRequest;

	/**
	 * Dispatched when a user first generates a context menu but before the contents of the context menu are displayed.
	 * @eventType flash.events.ContextMenuEvent.MENU_SELECT
	 */
	[Event(name="menuSelect", type="flash.events.ContextMenuEvent")] 

	/// The ContextMenu class provides control over the items in the Flash Player context menu.
	public class ContextMenu extends EventDispatcher
	{
		/// An object that has the following properties of the ContextMenuBuiltInItems class: forwardAndBack, loop, play, print, quality, rewind, save, and zoom.
		public function get builtInItems () : ContextMenuBuiltInItems;
		public function set builtInItems (value:ContextMenuBuiltInItems) : void;

		/// An object that has the following properties of the ContextMenuClipboardItems class: cut, copy, paste, delete, selectAll.
		public function get clipboardItems () : ContextMenuClipboardItems;
		public function set clipboardItems (value:ContextMenuClipboardItems) : void;

		/// Specifies whether or not the clipboard menu should be used.
		public function get clipboardMenu () : Boolean;
		public function set clipboardMenu (value:Boolean) : void;

		/// An array of ContextMenuItem objects.
		public function get customItems () : Array;
		public function set customItems (value:Array) : void;

		/// The URLRequest of the link.
		public function get link () : URLRequest;
		public function set link (value:URLRequest) : void;

		/// Creates a copy of the specified ContextMenu object.
		public function clone () : ContextMenu;

		/// Creates a ContextMenu object.
		public function ContextMenu ();

		/// Hides all built-in menu items (except Settings) in the specified ContextMenu object.
		public function hideBuiltInItems () : void;
	}
}
