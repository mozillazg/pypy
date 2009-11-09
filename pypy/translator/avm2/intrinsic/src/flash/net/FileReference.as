package flash.net
{
	import flash.events.EventDispatcher;
	import flash.net.URLRequest;
	import flash.utils.ByteArray;

	/**
	 * Dispatched after data is received from the server after a successful upload.
	 * @eventType flash.events.DataEvent.UPLOAD_COMPLETE_DATA
	 */
	[Event(name="uploadCompleteData", type="flash.events.DataEvent")] 

	/**
	 * Dispatched if a call to the upload() or uploadUnencoded() method attempts to access data over HTTP and Adobe AIR is able to detect and return the status code for the request.
	 * @eventType flash.events.HTTPStatusEvent.HTTP_RESPONSE_STATUS
	 */
	[Event(name="httpResponseStatus", type="flash.events.HTTPStatusEvent")] 

	/**
	 * Dispatched when an upload fails and an HTTP status code is available to describe the failure.
	 * @eventType flash.events.HTTPStatusEvent.HTTP_STATUS
	 */
	[Event(name="httpStatus", type="flash.events.HTTPStatusEvent")] 

	/**
	 * Dispatched when the user selects a file for upload or download from the file-browsing dialog box.
	 * @eventType flash.events.Event.SELECT
	 */
	[Event(name="select", type="flash.events.Event")] 

	/**
	 * Dispatched when a call to the FileReference.upload() or FileReference.download() method tries to upload a file to a server or get a file from a server that is outside the caller's security sandbox.
	 * @eventType flash.events.SecurityErrorEvent.SECURITY_ERROR
	 */
	[Event(name="securityError", type="flash.events.SecurityErrorEvent")] 

	/**
	 * Dispatched periodically during the file upload or download operation.
	 * @eventType flash.events.ProgressEvent.PROGRESS
	 */
	[Event(name="progress", type="flash.events.ProgressEvent")] 

	/**
	 * Dispatched when an upload or download operation starts.
	 * @eventType flash.events.Event.OPEN
	 */
	[Event(name="open", type="flash.events.Event")] 

	/**
	 * Dispatched when the upload or download fails.
	 * @eventType flash.events.IOErrorEvent.IO_ERROR
	 */
	[Event(name="ioError", type="flash.events.IOErrorEvent")] 

	/**
	 * Dispatched when download is complete or when upload generates an HTTP status code of 200.
	 * @eventType flash.events.Event.COMPLETE
	 */
	[Event(name="complete", type="flash.events.Event")] 

	/**
	 * Dispatched when a file upload or download is canceled through the file-browsing dialog box by the user.
	 * @eventType flash.events.Event.CANCEL
	 */
	[Event(name="cancel", type="flash.events.Event")] 

	/// The FileReference class provides a means to upload and download files between a user's computer and a server.
	public class FileReference extends EventDispatcher
	{
		/// The creation date of the file on the local disk.
		public function get creationDate () : Date;

		/// The Macintosh creator type of the file, which is only used in Mac OS versions prior to Mac OS X.
		public function get creator () : String;

		/// The ByteArray representing the loaded file after a successful call to load().
		public function get data () : ByteArray;

		/// The date that the file on the local disk was last modified.
		public function get modificationDate () : Date;

		/// The name of the file on the local disk.
		public function get name () : String;

		/// The size of the file on the local disk in bytes.
		public function get size () : uint;

		/// The file type.
		public function get type () : String;

		/// Displays a file-browsing dialog box that lets the user select a file to upload.
		public function browse (typeFilter:Array = null) : Boolean;

		/// Cancels any ongoing upload or download.
		public function cancel () : void;

		/// Opens a dialog box that lets the user download a file from a remote server.
		public function download (request:URLRequest, defaultFileName:String = null) : void;

		/// Creates a new FileReference object.
		public function FileReference ();

		/// Starts the load of a local file.
		public function load () : void;

		/// Opens a dialog box that lets the user save a file to the local filesystem.
		public function save (data:*, defaultFileName:String = null) : void;

		/// Starts the upload of a file to a remote server.
		public function upload (request:URLRequest, uploadDataFieldName:String = "Filedata", testUpload:Boolean = false) : void;
	}
}
