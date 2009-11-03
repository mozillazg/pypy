package flash.net
{
	import flash.net.URLRequest;

	/// Preserves the class (type) of an object when the object is encoded in Action Message Format (AMF).
	public function registerClassAlias (aliasName:String, classObject:Class) : void;

	/// Looks up a class that previously had an alias registered through a call to the registerClassAlias() method.
	public function getClassByAlias (aliasName:String) : Class;

	/// Opens or replaces a window in the application that contains the Flash Player container (usually a browser).
	public function navigateToURL (request:URLRequest, window:String = null) : void;

	/// Sends a URL request to a server, but ignores any response.
	public function sendToURL (request:URLRequest) : void;

}

