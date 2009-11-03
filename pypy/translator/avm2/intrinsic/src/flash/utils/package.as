package flash.utils
{
	/// Proxy methods namespace
	public namespace flash_proxy;

	/// Runs a function at a specified interval (in milliseconds).
	public function setInterval (closure:Function, delay:Number, ...arguments) : uint;

	/// Runs a specified function after a specified delay (in milliseconds).
	public function setTimeout (closure:Function, delay:Number, ...arguments) : uint;

	/// Cancels a specified setInterval() call.
	public function clearInterval (id:uint) : void;

	/// Cancels a specified setTimeout() call.
	public function clearTimeout (id:uint) : void;

	/// Produces an XML object that describes the ActionScript object named as the parameter of the method.
	public function describeType (value:*) : XML;

	/// Returns the fully qualified class name of an object.
	public function getQualifiedClassName (value:*) : String;

	/// Returns a reference to the class object of the class specified by the name parameter.
	public function getDefinitionByName (name:String) : Object;

	/// Returns the fully qualified class name of the base class of the object specified by the value parameter.
	public function getQualifiedSuperclassName (value:*) : String;

	/// Returns the number of milliseconds that have elapsed since Flash Player was initialized, and is used to compute relative time.
	public function getTimer () : int;

	/// Returns an escaped copy of the input string encoded as either UTF-8 or system code page, depending on the value of System.useCodePage.
	public function escapeMultiByte (value:String) : String;

	/// Returns an unescaped copy of the input string, which is decoded from either system code page page or UTF-8 depending on the value of System.useCodePage.
	public function unescapeMultiByte (value:String) : String;

}

