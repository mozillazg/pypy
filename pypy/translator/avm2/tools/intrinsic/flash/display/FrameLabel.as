package flash.display
{
	/// The FrameLabel object contains properties that specify a frame number and the corresponding label name.
	public class FrameLabel extends Object
	{
		/// The frame number containing the label.
		public function get frame () : int;

		/// The name of the label.
		public function get name () : String;

		public function FrameLabel (name:String, frame:int);
	}
}
