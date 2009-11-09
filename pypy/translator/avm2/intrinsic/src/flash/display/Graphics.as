package flash.display
{
	import flash.display.Shader;
	import flash.geom.Matrix;
	import flash.display.BitmapData;
	import flash.display.IGraphicsStroke;
	import flash.display.IGraphicsPath;
	import flash.display.IGraphicsFill;
	import flash.display.IGraphicsData;
	import flash.display.Graphics;

	/// The Graphics class contains a set of methods that you can use to create a vector shape.
	public class Graphics extends Object
	{
		/// Begins a bitmap filled shape.
		public function beginBitmapFill (bitmap:BitmapData, matrix:Matrix = null, repeat:Boolean = true, smooth:Boolean = false) : void;

		/// Specifies a single-color fill.
		public function beginFill (color:uint, alpha:Number = 1) : void;

		/// Specifies a gradient fill.
		public function beginGradientFill (type:String, colors:Array, alphas:Array, ratios:Array, matrix:Matrix = null, spreadMethod:String = "pad", interpolationMethod:String = "rgb", focalPointRatio:Number = 0) : void;

		/// Specifies a shader fill.
		public function beginShaderFill (shader:Shader, matrix:Matrix = null) : void;

		/// Clears the graphics that were drawn to this Graphics object, and resets fill and line style settings.
		public function clear () : void;

		/// Copies all of drawing commands from the source Graphics object into the calling Graphics object.
		public function copyFrom (sourceGraphics:Graphics) : void;

		/// Draws a curve from the current drawing position to (anchorX, anchorY) using the control point specified by (controlX, controlY).
		public function curveTo (controlX:Number, controlY:Number, anchorX:Number, anchorY:Number) : void;

		/// Draws a circle.
		public function drawCircle (x:Number, y:Number, radius:Number) : void;

		/// Draws an ellipse.
		public function drawEllipse (x:Number, y:Number, width:Number, height:Number) : void;

		/// Submits a series of IGraphicsData instances for drawing.
		public function drawGraphicsData (graphicsData:Vector.<IGraphicsData>) : void;

		/// Submits a series of commands for drawing.
		public function drawPath (commands:Vector.<int>, data:Vector.<Number>, winding:String = "evenOdd") : void;

		/// Draws a round rectangle.
		public function drawRect (x:Number, y:Number, width:Number, height:Number) : void;

		/// Draws a round rectangle.
		public function drawRoundRect (x:Number, y:Number, width:Number, height:Number, ellipseWidth:Number, ellipseHeight:Number = null) : void;

		public function drawRoundRectComplex (x:Number, y:Number, width:Number, height:Number, topLeftRadius:Number, topRightRadius:Number, bottomLeftRadius:Number, bottomRightRadius:Number) : void;

		/// Renders a set of triangles, typically to distort bitmaps and give them a three-dimensional appearance.
		public function drawTriangles (vertices:Vector.<Number>, indices:Vector.<int> = null, uvtData:Vector.<Number> = null, culling:String = "none") : void;

		/// Applies a fill to the lines and curves.
		public function endFill () : void;

		public function Graphics ();

		/// Specifies a bitmap to use for the line stroke when drawing lines.
		public function lineBitmapStyle (bitmap:BitmapData, matrix:Matrix = null, repeat:Boolean = true, smooth:Boolean = false) : void;

		/// Specifies a gradient to use for the stroke when drawing lines.
		public function lineGradientStyle (type:String, colors:Array, alphas:Array, ratios:Array, matrix:Matrix = null, spreadMethod:String = "pad", interpolationMethod:String = "rgb", focalPointRatio:Number = 0) : void;

		/// Specifies a shader to use for the line stroke when drawing lines.
		public function lineShaderStyle (shader:Shader, matrix:Matrix = null) : void;

		/// Specifies a line style that Flash uses for drawing lines.
		public function lineStyle (thickness:Number = null, color:uint = 0, alpha:Number = 1, pixelHinting:Boolean = false, scaleMode:String = "normal", caps:String = null, joints:String = null, miterLimit:Number = 3) : void;

		/// Draws a line from the current drawing position to (x, y).
		public function lineTo (x:Number, y:Number) : void;

		/// Moves the current drawing position to (x, y).
		public function moveTo (x:Number, y:Number) : void;
	}
}
