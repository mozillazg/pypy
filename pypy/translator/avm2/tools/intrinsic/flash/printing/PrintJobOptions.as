package flash.printing
{
	/// The PrintJobOptions class contains properties to use with the options parameter of the PrintJob.addPage() method.
	public class PrintJobOptions extends Object
	{
		/// Specifies whether the content in the print job is printed as a bitmap or as a vector.
		public var printAsBitmap : Boolean;

		/// Creates a new PrintJobOptions object.
		public function PrintJobOptions (printAsBitmap:Boolean = false);
	}
}
