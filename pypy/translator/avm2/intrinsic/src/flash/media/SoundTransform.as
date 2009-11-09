package flash.media
{
	/// The SoundTransform class contains properties for volume and panning.
	public class SoundTransform extends Object
	{
		/// A value, from 0 (none) to 1 (all), specifying how much of the left input is played in the left speaker.
		public function get leftToLeft () : Number;
		public function set leftToLeft (leftToLeft:Number) : void;

		/// A value, from 0 (none) to 1 (all), specifying how much of the left input is played in the right speaker.
		public function get leftToRight () : Number;
		public function set leftToRight (leftToRight:Number) : void;

		/// The left-to-right panning of the sound, ranging from -1 (full pan left) to 1 (full pan right).
		public function get pan () : Number;
		public function set pan (panning:Number) : void;

		/// A value, from 0 (none) to 1 (all), specifying how much of the right input is played in the left speaker.
		public function get rightToLeft () : Number;
		public function set rightToLeft (rightToLeft:Number) : void;

		/// A value, from 0 (none) to 1 (all), specifying how much of the right input is played in the right speaker.
		public function get rightToRight () : Number;
		public function set rightToRight (rightToRight:Number) : void;

		/// The volume, ranging from 0 (silent) to 1 (full volume).
		public function get volume () : Number;
		public function set volume (volume:Number) : void;

		/// Creates a SoundTransform object.
		public function SoundTransform (vol:Number = 1, panning:Number = 0);
	}
}
