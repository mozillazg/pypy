package flash.text.engine
{
	import flash.text.engine.TextJustifier;

	/// The SpaceJustifier class represents properties that control the justification options for text lines in a text block.
	public class SpaceJustifier extends TextJustifier
	{
		/// Specifies whether to use letter spacing during justification.
		public function get letterSpacing () : Boolean;
		public function set letterSpacing (value:Boolean) : void;

		/// Constructs a cloned copy of the SpaceJustifier.
		public function clone () : TextJustifier;

		/// Creates a SpaceJustifier object.
		public function SpaceJustifier (locale:String = "en", lineJustification:String = "unjustified", letterSpacing:Boolean = false);
	}
}
