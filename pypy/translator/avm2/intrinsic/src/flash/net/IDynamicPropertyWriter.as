package flash.net
{
	import flash.net.IDynamicPropertyOutput;

	/// This interface is used with the IDynamicPropertyOutput interface to control the serialization of dynamic properties of dynamic objects.
	public interface IDynamicPropertyWriter
	{
		/// Writes the name and value of an IDynamicPropertyOutput object to an object with dynamic properties.
		public function writeDynamicProperties (obj:Object, output:IDynamicPropertyOutput) : void;
	}
}
