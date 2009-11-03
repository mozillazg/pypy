package flash.display
{
	import flash.events.EventDispatcher;
	import flash.display.LoaderInfo;
	import flash.events.Event;
	import flash.utils.ByteArray;
	import flash.system.ApplicationDomain;
	import flash.display.Loader;
	import flash.display.DisplayObject;

	/**
	 * Dispatched when a network request is made over HTTP and Flash Player can detect the HTTP status code.
	 * @eventType flash.events.HTTPStatusEvent.HTTP_STATUS
	 */
	[Event(name="httpStatus", type="flash.events.HTTPStatusEvent")] 

	/**
	 * Dispatched by a LoaderInfo object whenever a loaded object is removed by using the unload() method of the Loader object, or when a second load is performed by the same Loader object and the original content is removed prior to the load beginning.
	 * @eventType flash.events.Event.UNLOAD
	 */
	[Event(name="unload", type="flash.events.Event")] 

	/**
	 * Dispatched when data is received as the download operation progresses.
	 * @eventType flash.events.ProgressEvent.PROGRESS
	 */
	[Event(name="progress", type="flash.events.ProgressEvent")] 

	/**
	 * Dispatched when a load operation starts.
	 * @eventType flash.events.Event.OPEN
	 */
	[Event(name="open", type="flash.events.Event")] 

	/**
	 * Dispatched when an input or output error occurs that causes a load operation to fail.
	 * @eventType flash.events.IOErrorEvent.IO_ERROR
	 */
	[Event(name="ioError", type="flash.events.IOErrorEvent")] 

	/**
	 * Dispatched when the properties and methods of a loaded SWF file are accessible and ready for use.
	 * @eventType flash.events.Event.INIT
	 */
	[Event(name="init", type="flash.events.Event")] 

	/**
	 * Dispatched when data has loaded successfully.
	 * @eventType flash.events.Event.COMPLETE
	 */
	[Event(name="complete", type="flash.events.Event")] 

	/// The LoaderInfo class provides information about a loaded SWF file or a loaded image file (JPEG, GIF, or PNG).
	public class LoaderInfo extends EventDispatcher
	{
		/// The ActionScript version of the loaded SWF file.
		public function get actionScriptVersion () : uint;

		/// When an external SWF file is loaded, all ActionScript 3.0 definitions contained in the loaded class are stored in the applicationDomain property.
		public function get applicationDomain () : ApplicationDomain;

		/// The bytes associated with a LoaderInfo object.
		public function get bytes () : ByteArray;

		/// The number of bytes that are loaded for the media.
		public function get bytesLoaded () : uint;

		/// The number of compressed bytes in the entire media file.
		public function get bytesTotal () : uint;

		/// Expresses the trust relationship from content (child) to the Loader (parent).
		public function get childAllowsParent () : Boolean;

		/// The loaded object associated with this LoaderInfo object.
		public function get content () : DisplayObject;

		/// The MIME type of the loaded file.
		public function get contentType () : String;

		/// The nominal frame rate, in frames per second, of the loaded SWF file.
		public function get frameRate () : Number;

		/// The nominal height of the loaded file.
		public function get height () : int;

		/// The Loader object associated with this LoaderInfo object.
		public function get loader () : Loader;

		/// The URL of the SWF file that initiated the loading of the media described by this LoaderInfo object.
		public function get loaderURL () : String;

		/// An object that contains name-value pairs that represent the parameters provided to the loaded SWF file.
		public function get parameters () : Object;

		/// Expresses the trust relationship from Loader (parent) to the content (child).
		public function get parentAllowsChild () : Boolean;

		/// Expresses the domain relationship between the loader and the content: true if they have the same origin domain; false otherwise.
		public function get sameDomain () : Boolean;

		/// An EventDispatcher instance that can be used to exchange events across security boundaries.
		public function get sharedEvents () : EventDispatcher;

		/// The file format version of the loaded SWF file.
		public function get swfVersion () : uint;

		/// The URL of the media being loaded.
		public function get url () : String;

		/// The nominal width of the loaded content.
		public function get width () : int;

		public function dispatchEvent (event:Event) : Boolean;

		/// Returns the LoaderInfo object associated with a SWF file defined as an object.
		public static function getLoaderInfoByDefinition (object:Object) : LoaderInfo;

		public function LoaderInfo ();
	}
}
