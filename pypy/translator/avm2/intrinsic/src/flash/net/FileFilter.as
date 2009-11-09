package flash.net
{
	/// The FileFilter class is used to indicate what files on the user's system are shown in the file-browsing dialog box that is displayed when FileReference.browse() or FileReferenceList.browse() is called.
	public class FileFilter extends Object
	{
		/// The description string for the filter.
		public function get description () : String;
		public function set description (value:String) : void;

		/// A list of file extensions.
		public function get extension () : String;
		public function set extension (value:String) : void;

		/// A list of Macintosh file types.
		public function get macType () : String;
		public function set macType (value:String) : void;

		/// Creates a new FileFilter instance.
		public function FileFilter (description:String, extension:String, macType:String = null);
	}
}
