package flash.utils
{
	/// The Endian class contains values that denote the byte order used to represent multibyte numbers.
	public class Endian extends Object
	{
		/// Indicates the most significant byte of the multibyte number appears first in the sequence of bytes.
		public static const BIG_ENDIAN : String;
		/// Indicates the least significant byte of the multibyte number appears first in the sequence of bytes.
		public static const LITTLE_ENDIAN : String;

		public function Endian ();
	}
}
