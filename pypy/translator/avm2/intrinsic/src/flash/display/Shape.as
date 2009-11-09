package flash.display
{
	import flash.display.Graphics;

	/// The Shape class is used to create lightweight shapes by using the ActionScript drawing application program interface (API).
	public class Shape extends DisplayObject
	{
		/// Specifies the Graphics object belonging to this Shape object, where vector drawing commands can occur.
		public function get graphics () : Graphics;

		/// Creates a new Shape object.
		public function Shape ();
	}
}
