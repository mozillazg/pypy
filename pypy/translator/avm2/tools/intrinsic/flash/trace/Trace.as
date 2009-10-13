package flash.trace
{
	public class Trace extends Object
	{
		public static const FILE : *;
		public static const LISTENER : *;
		public static const METHODS : int;
		public static const METHODS_AND_LINES : int;
		public static const METHODS_AND_LINES_WITH_ARGS : int;
		public static const METHODS_WITH_ARGS : int;
		public static const OFF : int;

		public static function getLevel (target:int = 2) : int;

		public static function getListener () : Function;

		public static function setLevel (l:int, target:int = 2) : *;

		public static function setListener (f:Function) : *;

		public function Trace ();
	}
}
