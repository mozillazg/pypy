package flash.system
{
	import flash.system.ApplicationDomain;
	import flash.utils.ByteArray;

	/// The ApplicationDomain class is a container for discrete groups of class definitions.
	public class ApplicationDomain extends Object
	{
		/// Gets the current application domain in which your code is executing.
		public static function get currentDomain () : ApplicationDomain;

		/// Gets and sets the object on which domain-global memory operations will operate within this ApplicationDomain.
		public function get domainMemory () : ByteArray;
		public function set domainMemory (mem:ByteArray) : void;

		/// Gets the minimum memory object length required to be used as ApplicationDomain.domainMemory.
		public static function get MIN_DOMAIN_MEMORY_LENGTH () : uint;

		/// Gets the parent domain of this application domain.
		public function get parentDomain () : ApplicationDomain;

		/// Creates a new application domain.
		public function ApplicationDomain (parentDomain:ApplicationDomain = null);

		/// Gets a public definition from the specified application domain.
		public function getDefinition (name:String) : Object;

		/// Checks to see if a public definition exists within the specified application domain.
		public function hasDefinition (name:String) : Boolean;
	}
}
