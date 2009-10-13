package flash.display
{
	/// Defines the values to use for specifying path-drawing commands.
	public class GraphicsPathCommand extends Object
	{
		/// Specifies a drawing command that draws a curve from the current drawing position to the x- and y-coordinates specified in the data vector, using a control point.
		public static const CURVE_TO : int;
		/// Specifies a drawing command that draws a line from the current drawing position to the x- and y-coordinates specified in the data vector.
		public static const LINE_TO : int;
		/// Specifies a drawing command that moves the current drawing position to the x- and y-coordinates specified in the data vector.
		public static const MOVE_TO : int;
		/// Represents the default "do nothing" command.
		public static const NO_OP : int;
		/// Specifies a "line to" drawing command, but uses two sets of coordinates (four values) instead of one set.
		public static const WIDE_LINE_TO : int;
		/// Specifies a "move to" drawing command, but uses two sets of coordinates (four values) instead of one set.
		public static const WIDE_MOVE_TO : int;

		public function GraphicsPathCommand ();
	}
}
