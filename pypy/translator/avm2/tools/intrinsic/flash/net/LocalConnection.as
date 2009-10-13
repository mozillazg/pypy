package flash.net
{
	import flash.events.EventDispatcher;

	/**
	 * Dispatched when a LocalConnection object reports its status.
	 * @eventType flash.events.StatusEvent.STATUS
	 */
	[Event(name="status", type="flash.events.StatusEvent")] 

	/**
	 * Dispatched if a call to LocalConnection.send() attempts to send data to a different security sandbox.
	 * @eventType flash.events.SecurityErrorEvent.SECURITY_ERROR
	 */
	[Event(name="securityError", type="flash.events.SecurityErrorEvent")] 

	/**
	 * Dispatched when an exception is thrown asynchronously -- that is, from native asynchronous code.
	 * @eventType flash.events.AsyncErrorEvent.ASYNC_ERROR
	 */
	[Event(name="asyncError", type="flash.events.AsyncErrorEvent")] 

	/// The LocalConnection class lets you create a LocalConnection object that can invoke a method in another LocalConnection object, either within a single SWF file or between multiple SWF files.
	public class LocalConnection extends EventDispatcher
	{
		/// Indicates the object on which callback methods are invoked.
		public function get client () : Object;
		public function set client (client:Object) : void;

		/// A string representing the domain of the location of the current SWF file.
		public function get domain () : String;

		/// Specifies one or more domains that can send LocalConnection calls to this LocalConnection instance.
		public function allowDomain (...rest) : void;

		/// Specifies one or more domains that can send LocalConnection calls to this LocalConnection object.
		public function allowInsecureDomain (...rest) : void;

		/// Closes (disconnects) a LocalConnection object.
		public function close () : void;

		/// Prepares a LocalConnection object to receive commands from a send() command (called the sending LocalConnection object).
		public function connect (connectionName:String) : void;

		/// Creates a LocalConnection object.
		public function LocalConnection ();

		/// Invokes the method named methodName on a connection opened with the connect(<code>connectionName<code>) method (the receiving LocalConnection object).
		public function send (connectionName:String, methodName:String, ...rest) : void;
	}
}
