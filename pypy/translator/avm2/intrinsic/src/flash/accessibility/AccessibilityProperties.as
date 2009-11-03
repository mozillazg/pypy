package flash.accessibility
{
	/// The AccessibilityProperties class lets you control the presentation of Flash objects to accessibility aids, such as screen readers.
	public class AccessibilityProperties extends Object
	{
		/// Provides a description for this display object in the accessible presentation.
		public var description : String;
		/// If true, causes Flash Player to exclude child objects within this display object from the accessible presentation.
		public var forceSimple : Boolean;
		/// Provides a name for this display object in the accessible presentation.
		public var name : String;
		/// If true, disables the Flash Player default auto-labeling system.
		public var noAutoLabeling : Boolean;
		/// Indicates a keyboard shortcut associated with this display object.
		public var shortcut : String;
		/// If true, excludes this display object from accessible presentation.
		public var silent : Boolean;

		/// Creates a new AccessibilityProperties object.
		public function AccessibilityProperties ();
	}
}
