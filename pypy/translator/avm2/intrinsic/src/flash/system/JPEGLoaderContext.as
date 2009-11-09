package flash.system
{
	import flash.system.ApplicationDomain;
	import flash.system.SecurityDomain;

	public class JPEGLoaderContext extends LoaderContext
	{
		public var deblockingFilter : Number;

		public function JPEGLoaderContext (deblockingFilter:Number = 0, checkPolicyFile:Boolean = false, applicationDomain:ApplicationDomain = null, securityDomain:SecurityDomain = null);
	}
}
