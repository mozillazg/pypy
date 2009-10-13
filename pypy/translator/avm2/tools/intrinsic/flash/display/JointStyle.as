package flash.display
{
	/// The JointStyle class is an enumeration of constant values that specify the joint style to use in drawing lines.
	public class JointStyle extends Object
	{
		/// Specifies beveled joints in the joints parameter of the flash.display.Graphics.lineStyle() method.
		public static const BEVEL : String;
		/// Specifies mitered joints in the joints parameter of the flash.display.Graphics.lineStyle() method.
		public static const MITER : String;
		/// Specifies round joints in the joints parameter of the flash.display.Graphics.lineStyle() method.
		public static const ROUND : String;

		public function JointStyle ();
	}
}
