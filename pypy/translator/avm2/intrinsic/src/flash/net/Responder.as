package flash.net
{
	/// The Responder class provides an object that is used in NetConnection.call() to handle return values from the server related to the success or failure of specific operations.
	public class Responder extends Object
	{
		/// Creates a new Responder object.
		public function Responder (result:Function, status:Function = null);
	}
}
