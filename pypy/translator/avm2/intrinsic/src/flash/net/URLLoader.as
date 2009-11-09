package flash.net
{
	import flash.events.EventDispatcher;
	import flash.net.URLStream;
	import flash.net.URLRequest;
	import flash.events.ProgressEvent;
	import flash.events.Event;

	/**
	 * Dispatched if a call to URLLoader.load() attempts to access data over HTTP and the current Flash Player environment is able to detect and return the status code for the request.
	 * @eventType flash.events.HTTPStatusEvent.HTTP_STATUS
	 */
	[Event(name="httpStatus", type="flash.events.HTTPStatusEvent")] 

	/**
	 * Dispatched if a call to URLLoader.load() attempts to load data from a server outside the security sandbox.
	 * @eventType flash.events.SecurityErrorEvent.SECURITY_ERROR
	 */
	[Event(name="securityError", type="flash.events.SecurityErrorEvent")] 

	/**
	 * Dispatched if a call to URLLoader.load() results in a fatal error that terminates the download.
	 * @eventType flash.events.IOErrorEvent.IO_ERROR
	 */
	[Event(name="ioError", type="flash.events.IOErrorEvent")] 

	/**
	 * Dispatched when data is received as the download operation progresses.
	 * @eventType flash.events.ProgressEvent.PROGRESS
	 */
	[Event(name="progress", type="flash.events.ProgressEvent")] 

	/**
	 * Dispatched after all the received data is decoded and placed in the data property of the URLLoader object.
	 * @eventType flash.events.Event.COMPLETE
	 */
	[Event(name="complete", type="flash.events.Event")] 

	/**
	 * Dispatched when the download operation commences following a call to the URLLoader.load() method.
	 * @eventType flash.events.Event.OPEN
	 */
	[Event(name="open", type="flash.events.Event")] 

	/// The URLLoader class downloads data from a URL as text, binary data, or URL-encoded variables.
	public class URLLoader extends EventDispatcher
	{
		/// Indicates the number of bytes that have been loaded thus far during the load operation.
		public var bytesLoaded : uint;
		/// Indicates the total number of bytes in the downloaded data.
		public var bytesTotal : uint;
		/// The data received from the load operation.
		public var data : *;
		/// Controls whether the downloaded data is received as text (URLLoaderDataFormat.TEXT), raw binary data (URLLoaderDataFormat.BINARY), or URL-encoded variables (URLLoaderDataFormat.VARIABLES).
		public var dataFormat : String;

		/// Closes the load operation in progress.
		public function close () : void;

		/// Sends and loads data from the specified URL.
		public function load (request:URLRequest) : void;

		/// Creates a URLLoader object.
		public function URLLoader (request:URLRequest = null);
	}
}
