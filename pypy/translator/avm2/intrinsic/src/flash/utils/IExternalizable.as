package flash.utils
{
	import flash.utils.IDataInput;
	import flash.utils.IDataOutput;

	/// The IExternalizable interface provides control over serialization of a class as it is encoded into a data stream.
	public interface IExternalizable
	{
		/// A class implements this method to decode itself from a data stream by calling the methods of the IDataInput interface.
		public function readExternal (input:IDataInput) : void;

		/// A class implements this method to encode itself for a data stream by calling the methods of the IDataOutput interface.
		public function writeExternal (output:IDataOutput) : void;
	}
}
