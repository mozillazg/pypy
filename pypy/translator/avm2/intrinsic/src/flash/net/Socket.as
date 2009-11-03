package flash.net
{
	import flash.events.EventDispatcher;
	import flash.events.TimerEvent;
	import flash.events.SecurityErrorEvent;
	import flash.utils.IDataInput;
	import flash.utils.IDataOutput;
	import flash.utils.Timer;
	import flash.utils.ByteArray;

	/**
	 * Dispatched if a call to Socket.connect() attempts to connect either to a server outside the caller's security sandbox or to a port lower than 1024.
	 * @eventType flash.events.SecurityErrorEvent.SECURITY_ERROR
	 */
	[Event(name="securityError", type="flash.events.SecurityErrorEvent")] 

	/**
	 * Dispatched when a socket has received data.
	 * @eventType flash.events.ProgressEvent.SOCKET_DATA
	 */
	[Event(name="socketData", type="flash.events.ProgressEvent")] 

	/**
	 * Dispatched when an input/output error occurs that causes a send or load operation to fail.
	 * @eventType flash.events.IOErrorEvent.IO_ERROR
	 */
	[Event(name="ioError", type="flash.events.IOErrorEvent")] 

	/**
	 * Dispatched when a network connection has been established.
	 * @eventType flash.events.Event.CONNECT
	 */
	[Event(name="connect", type="flash.events.Event")] 

	/**
	 * Dispatched when the server closes the socket connection.
	 * @eventType flash.events.Event.CLOSE
	 */
	[Event(name="close", type="flash.events.Event")] 

	/// The Socket class enables ActionScript code to make socket connections and to read and write raw binary data.
	public class Socket extends EventDispatcher implements IDataInput, IDataOutput
	{
		/// The number of bytes of data available for reading in the input buffer.
		public function get bytesAvailable () : uint;

		/// Indicates whether this Socket object is currently connected.
		public function get connected () : Boolean;

		/// Indicates the byte order for the data; possible values are constants from the flash.utils.Endian class, Endian.BIG_ENDIAN or Endian.LITTLE_ENDIAN.
		public function get endian () : String;
		public function set endian (type:String) : void;

		/// Controls the version of AMF used when writing or reading an object.
		public function get objectEncoding () : uint;
		public function set objectEncoding (version:uint) : void;

		/// Indicates the number of milliseconds to wait for a connection.
		public function get timeout () : uint;
		public function set timeout (value:uint) : void;

		/// Closes the socket.
		public function close () : void;

		/// Connects the socket to the specified host and port.
		public function connect (host:String, port:int) : void;

		/// Flushes any accumulated data in the socket's output buffer.
		public function flush () : void;

		/// Reads a Boolean value from the socket.
		public function readBoolean () : Boolean;

		/// Reads a signed byte from the socket.
		public function readByte () : int;

		/// Reads the number of data bytes specified by the length parameter from the socket.
		public function readBytes (bytes:ByteArray, offset:uint = 0, length:uint = 0) : void;

		/// Reads an IEEE 754 double-precision floating-point number from the socket.
		public function readDouble () : Number;

		/// Reads an IEEE 754 single-precision floating-point number from the socket.
		public function readFloat () : Number;

		/// Reads a signed 32-bit integer from the socket.
		public function readInt () : int;

		/// Reads a multibyte string from the byte stream, using the specified character set.
		public function readMultiByte (length:uint, charSet:String) : String;

		/// Reads an object from the socket, encoded in AMF serialized format.
		public function readObject () : *;

		/// Reads a signed 16-bit integer from the socket.
		public function readShort () : int;

		/// Reads an unsigned byte from the socket.
		public function readUnsignedByte () : uint;

		/// Reads an unsigned 32-bit integer from the socket.
		public function readUnsignedInt () : uint;

		/// Reads an unsigned 16-bit integer from the socket.
		public function readUnsignedShort () : uint;

		/// Reads a UTF-8 string from the socket.
		public function readUTF () : String;

		/// Reads the number of UTF-8 data bytes specified by the length parameter from the socket, and returns a string.
		public function readUTFBytes (length:uint) : String;

		/// Creates a new Socket object.
		public function Socket (host:String = null, port:int = 0);

		/// Writes a Boolean value to the socket.
		public function writeBoolean (value:Boolean) : void;

		/// Writes a byte to the socket.
		public function writeByte (value:int) : void;

		/// Writes a sequence of bytes from the specified byte array.
		public function writeBytes (bytes:ByteArray, offset:uint = 0, length:uint = 0) : void;

		/// Writes an IEEE 754 double-precision floating-point number to the socket.
		public function writeDouble (value:Number) : void;

		/// Writes an IEEE 754 single-precision floating-point number to the socket.
		public function writeFloat (value:Number) : void;

		/// Writes a 32-bit signed integer to the socket.
		public function writeInt (value:int) : void;

		/// Writes a multibyte string from the byte stream, using the specified character set.
		public function writeMultiByte (value:String, charSet:String) : void;

		/// Write an object to the socket in AMF serialized format.
		public function writeObject (object:*) : void;

		/// Writes a 16-bit integer to the socket.
		public function writeShort (value:int) : void;

		/// Writes a 32-bit unsigned integer to the socket.
		public function writeUnsignedInt (value:uint) : void;

		/// Writes the following data to the socket: a 16-bit unsigned integer, which indicates the length of the specified UTF-8 string in bytes, followed by the string itself.
		public function writeUTF (value:String) : void;

		/// Writes a UTF-8 string to the socket.
		public function writeUTFBytes (value:String) : void;
	}
}
