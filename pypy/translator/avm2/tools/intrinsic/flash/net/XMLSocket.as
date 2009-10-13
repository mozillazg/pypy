package flash.net
{
	import flash.events.EventDispatcher;
	import flash.utils.ByteArray;
	import flash.net.Socket;
	import flash.events.ProgressEvent;
	import flash.events.Event;

	/**
	 * Dispatched if a call to the XMLSocket.connect() method attempts to connect either to a server outside the caller's security sandbox or to a port lower than 1024.
	 * @eventType flash.events.SecurityErrorEvent.SECURITY_ERROR
	 */
	[Event(name="securityError", type="flash.events.SecurityErrorEvent")] 

	/**
	 * Dispatched when an input/output error occurs that causes a send or receive operation to fail.
	 * @eventType flash.events.IOErrorEvent.IO_ERROR
	 */
	[Event(name="ioError", type="flash.events.IOErrorEvent")] 

	/**
	 * Dispatched after raw data is sent or received.
	 * @eventType flash.events.DataEvent.DATA
	 */
	[Event(name="data", type="flash.events.DataEvent")] 

	/**
	 * Dispatched after a successful call to the XMLSocket.connect() method.
	 * @eventType flash.events.Event.CONNECT
	 */
	[Event(name="connect", type="flash.events.Event")] 

	/**
	 * Dispatched when the server closes the socket connection.
	 * @eventType flash.events.Event.CLOSE
	 */
	[Event(name="close", type="flash.events.Event")] 

	/// The XMLSocket class implements client sockets that let the computer that is running Flash Player communicate with a server computer identified by an IP address or domain name.
	public class XMLSocket extends EventDispatcher
	{
		/// Indicates whether this XMLSocket object is currently connected.
		public function get connected () : Boolean;

		/// Indicates the number of milliseconds to wait for a connection.
		public function get timeout () : int;
		public function set timeout (value:int) : void;

		/// Closes the connection specified by the XMLSocket object.
		public function close () : void;

		/// Establishes a connection to the specified Internet host using the specified TCP port.
		public function connect (host:String, port:int) : void;

		/// Converts the XML object or data specified in the object parameter to a string and transmits it to the server, followed by a zero (0) byte.
		public function send (object:*) : void;

		/// Creates a new XMLSocket object.
		public function XMLSocket (host:String = null, port:int = 0);
	}
}
