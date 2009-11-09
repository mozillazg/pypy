package flash.display
{
	import flash.events.EventDispatcher;
	import flash.display.Shader;

	/**
	 * Dispatched when the ShaderJob finishes processing the data using the shader.
	 * @eventType flash.events.ShaderEvent.COMPLETE
	 */
	[Event(name="complete", type="flash.events.ShaderEvent")] 

	/// A ShaderJob instance is used to execute a shader operation in the background.
	public class ShaderJob extends EventDispatcher
	{
		/// The height of the result data in the target if it is a ByteArray or Vector.<Number> instance.
		public function get height () : int;
		public function set height (v:int) : void;

		/// The progress of a running shader.
		public function get progress () : Number;

		/// The shader that's used for the operation.
		public function get shader () : Shader;
		public function set shader (s:Shader) : void;

		/// The object into which the result of the shader operation is written.
		public function get target () : Object;
		public function set target (s:Object) : void;

		/// The width of the result data in the target if it is a ByteArray or Vector.<Number> instance.
		public function get width () : int;
		public function set width (v:int) : void;

		/// Cancels the currently running shader operation.
		public function cancel () : void;

		/// A ShaderJob instance is used to execute a shader operation in the background.
		public function ShaderJob (shader:Shader = null, target:Object = null, width:int = 0, height:int = 0);

		/// Starts a background shader operation.
		public function start (waitForCompletion:Boolean = false) : void;
	}
}
