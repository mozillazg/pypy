package flash.net
{
	import flash.events.EventDispatcher;

	/**
	 * Dispatched when the user selects one or more files to upload from the file-browsing dialog box.
	 * @eventType flash.events.Event.SELECT
	 */
	[Event(name="select", type="flash.events.Event")] 

	/**
	 * Dispatched when the user dismisses the file-browsing dialog box.
	 * @eventType flash.events.Event.CANCEL
	 */
	[Event(name="cancel", type="flash.events.Event")] 

	/// The FileReferenceList class provides a means to let users select one or more files for uploading.
	public class FileReferenceList extends EventDispatcher
	{
		/// An array of FileReference objects.
		public function get fileList () : Array;

		/// Displays a file-browsing dialog box that lets the user select local files to upload.
		public function browse (typeFilter:Array = null) : Boolean;

		/// Creates a new FileReferenceList object.
		public function FileReferenceList ();
	}
}
