package flash.text
{
	import flash.text.TextFormat;

	public class TextRun extends Object
	{
		public var beginIndex : int;
		public var endIndex : int;
		public var textFormat : TextFormat;

		public function TextRun (beginIndex:int, endIndex:int, textFormat:TextFormat);
	}
}
