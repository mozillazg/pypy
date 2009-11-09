package flash.ui
{
	/// The Keyboard class is used to build an interface that can be controlled by a user with a standard keyboard.
	public class Keyboard extends Object
	{
		/// Constant associated with the key code value for the Backspace key (8).
		public static const BACKSPACE : uint;
		/// Constant associated with the key code value for the Caps Lock key (20).
		public static const CAPS_LOCK : uint;
		/// Constant associated with the key code value for the Control key (17).
		public static const CONTROL : uint;
		/// Constant associated with the key code value for the Delete key (46).
		public static const DELETE : uint;
		/// Constant associated with the key code value for the Down Arrow key (40).
		public static const DOWN : uint;
		/// Constant associated with the key code value for the End key (35).
		public static const END : uint;
		/// Constant associated with the key code value for the Enter key (13).
		public static const ENTER : uint;
		/// Constant associated with the key code value for the Escape key (27).
		public static const ESCAPE : uint;
		/// Constant associated with the key code value for the F1 key (112).
		public static const F1 : uint;
		/// Constant associated with the key code value for the F10 key (121).
		public static const F10 : uint;
		/// Constant associated with the key code value for the F11 key (122).
		public static const F11 : uint;
		/// Constant associated with the key code value for the F12 key (123).
		public static const F12 : uint;
		/// Constant associated with the key code value for the F13 key (124).
		public static const F13 : uint;
		/// Constant associated with the key code value for the F14 key (125).
		public static const F14 : uint;
		/// Constant associated with the key code value for the F15 key (126).
		public static const F15 : uint;
		/// Constant associated with the key code value for the F2 key (113).
		public static const F2 : uint;
		/// Constant associated with the key code value for the F3 key (114).
		public static const F3 : uint;
		/// Constant associated with the key code value for the F4 key (115).
		public static const F4 : uint;
		/// Constant associated with the key code value for the F5 key (116).
		public static const F5 : uint;
		/// Constant associated with the key code value for the F6 key (117).
		public static const F6 : uint;
		/// Constant associated with the key code value for the F7 key (118).
		public static const F7 : uint;
		/// Constant associated with the key code value for the F8 key (119).
		public static const F8 : uint;
		/// Constant associated with the key code value for the F9 key (120).
		public static const F9 : uint;
		/// Constant associated with the key code value for the Home key (36).
		public static const HOME : uint;
		/// Constant associated with the key code value for the Insert key (45).
		public static const INSERT : uint;
		/// Constant associated with the key code value for the Left Arrow key (37).
		public static const LEFT : uint;
		/// Constant associated with the key code value for the number 0 key on the number pad (96).
		public static const NUMPAD_0 : uint;
		/// Constant associated with the key code value for the number 1 key on the number pad (97).
		public static const NUMPAD_1 : uint;
		/// Constant associated with the key code value for the number 2 key on the number pad (98).
		public static const NUMPAD_2 : uint;
		/// Constant associated with the key code value for the number 3 key on the number pad (99).
		public static const NUMPAD_3 : uint;
		/// Constant associated with the key code value for the number 4 key on the number pad (100).
		public static const NUMPAD_4 : uint;
		/// Constant associated with the key code value for the number 5 key on the number pad (101).
		public static const NUMPAD_5 : uint;
		/// Constant associated with the key code value for the number 6 key on the number pad (102).
		public static const NUMPAD_6 : uint;
		/// Constant associated with the key code value for the number 7 key on the number pad (103).
		public static const NUMPAD_7 : uint;
		/// Constant associated with the key code value for the number 8 key on the number pad (104).
		public static const NUMPAD_8 : uint;
		/// Constant associated with the key code value for the number 9 key on the number pad (105).
		public static const NUMPAD_9 : uint;
		/// Constant associated with the key code value for the addition key on the number pad (107).
		public static const NUMPAD_ADD : uint;
		/// Constant associated with the key code value for the decimal key on the number pad (110).
		public static const NUMPAD_DECIMAL : uint;
		/// Constant associated with the key code value for the division key on the number pad (111).
		public static const NUMPAD_DIVIDE : uint;
		/// Constant associated with the key code value for the Enter key on the number pad (108).
		public static const NUMPAD_ENTER : uint;
		/// Constant associated with the key code value for the multiplication key on the number pad (106).
		public static const NUMPAD_MULTIPLY : uint;
		/// Constant associated with the key code value for the subtraction key on the number pad (109).
		public static const NUMPAD_SUBTRACT : uint;
		/// Constant associated with the key code value for the Page Down key (34).
		public static const PAGE_DOWN : uint;
		/// Constant associated with the key code value for the Page Up key (33).
		public static const PAGE_UP : uint;
		/// Constant associated with the key code value for the Right Arrow key (39).
		public static const RIGHT : uint;
		/// Constant associated with the key code value for the Shift key (16).
		public static const SHIFT : uint;
		/// Constant associated with the key code value for the Spacebar (32).
		public static const SPACE : uint;
		/// Constant associated with the key code value for the Tab key (9).
		public static const TAB : uint;
		/// Constant associated with the key code value for the Up Arrow key (38).
		public static const UP : uint;

		/// Specifies whether the Caps Lock key is activated (true) or not (false).
		public static function get capsLock () : Boolean;

		/// Specifies whether the Num Lock key is activated (true) or not (false).
		public static function get numLock () : Boolean;

		/// Specifies whether the last key pressed is accessible by other SWF files.
		public static function isAccessible () : Boolean;

		public function Keyboard ();
	}
}
