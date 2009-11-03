package flash.display
{
	import flash.display.LoaderInfo;
	import flash.net.URLRequest;
	import flash.system.ApplicationDomain;
	import flash.system.SecurityDomain;
	import flash.system.LoaderContext;
	import flash.display.DisplayObject;
	import flash.utils.ByteArray;

	/// The Loader class is used to load SWF files or image (JPG, PNG, or GIF) files.
	public class Loader extends DisplayObjectContainer
	{
		/// Contains the root display object of the SWF file or image (JPG, PNG, or GIF) file that was loaded by using the load() or loadBytes() methods.
		public function get content () : DisplayObject;

		/// Returns a LoaderInfo object corresponding to the object being loaded.
		public function get contentLoaderInfo () : LoaderInfo;

		public function addChild (child:DisplayObject) : DisplayObject;

		public function addChildAt (child:DisplayObject, index:int) : DisplayObject;

		/// Cancels a load() method operation that is currently in progress for the Loader instance.
		public function close () : void;

		/// Loads a SWF file or image file into a DisplayObject that is a child of this Loader instance.
		public function load (request:URLRequest, context:LoaderContext = null) : void;

		/// Loads from binary data stored in a ByteArray object.
		public function loadBytes (bytes:ByteArray, context:LoaderContext = null) : void;

		/// Creates a Loader object that you can use to load files, such as SWF, JPEG, GIF, or PNG files.
		public function Loader ();

		public function removeChild (child:DisplayObject) : DisplayObject;

		public function removeChildAt (index:int) : DisplayObject;

		public function setChildIndex (child:DisplayObject, index:int) : void;

		/// Removes a child of this Loader object that was loaded by using the load() method.
		public function unload () : void;

		/// Attempts to unload child SWF file contents and stops the execution of commands from loaded SWF files.
		public function unloadAndStop (gc:Boolean = true) : void;
	}
}
