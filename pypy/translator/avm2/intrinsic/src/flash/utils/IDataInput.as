package flash.utils
{
	import flash.utils.ByteArray;

	/// The IDataInput interface provides a set of methods for reading binary data.
	public interface IDataInput
	{
		/// Returns the number of bytes of data available for reading in the input buffer.
		public function get bytesAvailable () : uint;

		/// The byte order for the data, either the "bigEndian" or "littleEndian" constant from the Endian class.
		public function get endian () : String;
		public function set endian (type:String) : void;

		/// Used to determine whether the ActionScript 3.0, ActionScript 2.0, or ActionScript 1.0 format should be used when writing to, or reading binary data.
		public function get objectEncoding () : uint;
		public function set objectEncoding (version:uint) : void;

		/// Reads a Boolean value from the byte stream or byte array.
		public function readBoolean () : Boolean;

		/// Reads a signed byte from the byte stream or byte array.
		public function readByte () : int;

		/// Reads the number of data bytes, specified by the length parameter, from the byte stream or byte array.
		public function readBytes (bytes:ByteArray, offset:uint = 0, length:uint = 0) : void;

		/// Reads an IEEE 754 double-precision floating point number from the byte stream or byte array.
		public function readDouble () : Number;

		/// Reads an IEEE 754 single-precision floating point number from the byte stream or byte array.
		public function readFloat () : Number;

		/// Reads a signed 32-bit integer from the byte stream or byte array.
		public function readInt () : int;

		/// Reads a multibyte string of specified length from the byte stream using the specified character set.
		public function readMultiByte (length:uint, charSet:String) : String;

		/// Reads an object from the byte stream or byte array, encoded in AMF serialized format.
		public function readObject () : *;

		/// Reads a signed 16-bit integer from the byte stream or byte array.
		public function readShort () : int;

		/// Reads an unsigned byte from the byte stream or byte array.
		public function readUnsignedByte () : uint;

		/// Reads an unsigned 32-bit integer from the byte stream or byte array.
		public function readUnsignedInt () : uint;

		/// Reads an unsigned 16-bit integer from the byte stream or byte array.
		public function readUnsignedShort () : uint;

		/// Reads a UTF-8 string from the byte stream or byte array.
		public function readUTF () : String;

		/// Reads a sequence of length UTF-8 bytes from the byte stream or byte array and returns a string.
		public function readUTFBytes (length:uint) : String;
	}
}
