package flash.accessibility
{
	import flash.geom.Rectangle;

	public class AccessibilityImplementation extends Object
	{
		public var errno : uint;
		public var stub : Boolean;

		public function accDoDefaultAction (childID:uint) : void;

		public function AccessibilityImplementation ();

		public function accLocation (childID:uint) : *;

		public function accSelect (operation:uint, childID:uint) : void;

		public function get_accDefaultAction (childID:uint) : String;

		public function get_accFocus () : uint;

		public function get_accName (childID:uint) : String;

		public function get_accRole (childID:uint) : uint;

		public function get_accSelection () : Array;

		public function get_accState (childID:uint) : uint;

		public function get_accValue (childID:uint) : String;

		public function getChildIDArray () : Array;

		public function isLabeledBy (labelBounds:Rectangle) : Boolean;
	}
}
