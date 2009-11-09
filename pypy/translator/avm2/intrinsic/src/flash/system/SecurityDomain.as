package flash.system
{
	import flash.system.SecurityDomain;

	/// The SecurityDomain class represents the current security "sandbox," also known as a security domain.
	public class SecurityDomain extends Object
	{
		/// Gets the current security domain.
		public static function get currentDomain () : SecurityDomain;

		public function SecurityDomain ();
	}
}
