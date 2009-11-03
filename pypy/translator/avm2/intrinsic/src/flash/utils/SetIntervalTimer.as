package flash.utils
{
	import flash.events.Event;

	public class SetIntervalTimer extends Timer
	{
		public function SetIntervalTimer (closure:Function, delay:Number, repeats:Boolean, rest:Array);
	}
}
