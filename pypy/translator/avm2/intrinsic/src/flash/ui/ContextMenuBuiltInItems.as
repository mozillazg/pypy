package flash.ui
{
	import flash.ui.ContextMenuBuiltInItems;

	/// The ContextMenuBuiltInItems class describes the items that are built in to a context menu.
	public class ContextMenuBuiltInItems extends Object
	{
		/// Lets the user move forward or backward one frame in a SWF file at run time (does not appear for a single-frame SWF file).
		public var forwardAndBack : Boolean;
		/// Lets the user set a SWF file to start over automatically when it reaches the final frame (does not appear for a single-frame SWF file).
		public var loop : Boolean;
		/// Lets the user start a paused SWF file (does not appear for a single-frame SWF file).
		public var play : Boolean;
		/// Lets the user send the displayed frame image to a printer.
		public var print : Boolean;
		/// Lets the user set the resolution of the SWF file at run time.
		public var quality : Boolean;
		/// Lets the user set a SWF file to play from the first frame when selected, at any time (does not appear for a single-frame SWF file).
		public var rewind : Boolean;
		/// Lets the user with Shockmachine installed save a SWF file.
		public var save : Boolean;
		/// Lets the user zoom in and out on a SWF file at run time.
		public var zoom : Boolean;

		public function clone () : ContextMenuBuiltInItems;

		/// Creates a new ContextMenuBuiltInItems object so that you can set the properties for Flash Player to display or hide each menu item.
		public function ContextMenuBuiltInItems ();
	}
}
