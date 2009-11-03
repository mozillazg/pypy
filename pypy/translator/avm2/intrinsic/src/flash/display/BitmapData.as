package flash.display
{
	import flash.display.BitmapData;
	import flash.geom.Rectangle;
	import flash.geom.Point;
	import flash.filters.BitmapFilter;
	import flash.geom.ColorTransform;
	import flash.display.IBitmapDrawable;
	import flash.geom.Matrix;
	import flash.utils.ByteArray;

	/// The BitmapData class lets you work with the data (pixels) of a Bitmap object.
	public class BitmapData extends Object implements IBitmapDrawable
	{
		/// The height of the bitmap image in pixels.
		public function get height () : int;

		/// The rectangle that defines the size and location of the bitmap image.
		public function get rect () : Rectangle;

		/// Defines whether the bitmap image supports per-pixel transparency.
		public function get transparent () : Boolean;

		/// The width of the bitmap image in pixels.
		public function get width () : int;

		/// Takes a source image and a filter object and generates the filtered image.
		public function applyFilter (sourceBitmapData:BitmapData, sourceRect:Rectangle, destPoint:Point, filter:BitmapFilter) : void;

		/// Creates a BitmapData object with a specified width and height.
		public function BitmapData (width:int, height:int, transparent:Boolean = true, fillColor:uint = 4294967295);

		/// Returns a new BitmapData object with an exact copy of the original bitmap.
		public function clone () : BitmapData;

		/// Adjusts the color values in a specified area of a bitmap image by using a ColorTransform object.
		public function colorTransform (rect:Rectangle, colorTransform:ColorTransform) : void;

		/// Compares two BitmapData objects.
		public function compare (otherBitmapData:BitmapData) : Object;

		/// Transfers data from one channel of another BitmapData object or the current BitmapData object into a channel of the current BitmapData object.
		public function copyChannel (sourceBitmapData:BitmapData, sourceRect:Rectangle, destPoint:Point, sourceChannel:uint, destChannel:uint) : void;

		/// Provides a fast routine to perform pixel manipulation between images with no stretching, rotation, or color effects.
		public function copyPixels (sourceBitmapData:BitmapData, sourceRect:Rectangle, destPoint:Point, alphaBitmapData:BitmapData = null, alphaPoint:Point = null, mergeAlpha:Boolean = false) : void;

		/// Frees memory that is used to store the BitmapData object.
		public function dispose () : void;

		/// Draws the source display object onto the bitmap image, using the Flash Player vector renderer.
		public function draw (source:IBitmapDrawable, matrix:Matrix = null, colorTransform:ColorTransform = null, blendMode:String = null, clipRect:Rectangle = null, smoothing:Boolean = false) : void;

		/// Fills a rectangular area of pixels with a specified ARGB color.
		public function fillRect (rect:Rectangle, color:uint) : void;

		/// Performs a flood fill operation on an image starting at a (x, y) coordinate.
		public function floodFill (x:int, y:int, color:uint) : void;

		/// Determines the destination rectangle that will be affected by the applyFilter() call.
		public function generateFilterRect (sourceRect:Rectangle, filter:BitmapFilter) : Rectangle;

		/// Determines a rectangular region that either fully encloses all pixels of a specified color within the bitmap image (if the findColor parameter is set to true) or fully encloses all pixels that do not include the specified color (if the findColor parameter is set to false).
		public function getColorBoundsRect (mask:uint, color:uint, findColor:Boolean = true) : Rectangle;

		/// Returns an integer representing a RGB pixel value from a BitmapData object at a specific point.
		public function getPixel (x:int, y:int) : uint;

		/// Returns an ARGB color value that contains alpha channel data and RGB data.
		public function getPixel32 (x:int, y:int) : uint;

		/// Generates a byte array from a rectangular region of pixel data.
		public function getPixels (rect:Rectangle) : ByteArray;

		/// Generates a vector array from a rectangular region of pixel data.
		public function getVector (rect:Rectangle) : Vector.<uint>;

		/// Computes a 256 value binary number histogram of a BitmapData object.
		public function histogram (hRect:Rectangle = null) : Vector.<Vector.<Number>>;

		/// Performs pixel-level hit detection between one bitmap image and a point, rectangle, or other bitmap image.
		public function hitTest (firstPoint:Point, firstAlphaThreshold:uint, secondObject:Object, secondBitmapDataPoint:Point = null, secondAlphaThreshold:uint = 1) : Boolean;

		/// Locks an image so that any objects that reference the BitmapData object, such as Bitmap objects, are not updated when this BitmapData object changes.
		public function lock () : void;

		/// Performs per-channel blending from a source image to a destination image.
		public function merge (sourceBitmapData:BitmapData, sourceRect:Rectangle, destPoint:Point, redMultiplier:uint, greenMultiplier:uint, blueMultiplier:uint, alphaMultiplier:uint) : void;

		/// Fills an image with pixels representing random noise.
		public function noise (randomSeed:int, low:uint = 0, high:uint = 255, channelOptions:uint = 7, grayScale:Boolean = false) : void;

		/// Remaps the color channel values in an image that has up to four arrays of color palette data, one for each channel.
		public function paletteMap (sourceBitmapData:BitmapData, sourceRect:Rectangle, destPoint:Point, redArray:Array = null, greenArray:Array = null, blueArray:Array = null, alphaArray:Array = null) : void;

		/// Generates a Perlin noise image.
		public function perlinNoise (baseX:Number, baseY:Number, numOctaves:uint, randomSeed:int, stitch:Boolean, fractalNoise:Boolean, channelOptions:uint = 7, grayScale:Boolean = false, offsets:Array = null) : void;

		/// Performs a pixel dissolve either from a source image to a destination image or by using the same image.
		public function pixelDissolve (sourceBitmapData:BitmapData, sourceRect:Rectangle, destPoint:Point, randomSeed:int = 0, numPixels:int = 0, fillColor:uint = 0) : int;

		/// Scrolls an image by a certain (x, y) pixel amount.
		public function scroll (x:int, y:int) : void;

		/// Sets a single pixel of a BitmapData object.
		public function setPixel (x:int, y:int, color:uint) : void;

		/// Sets the color and alpha transparency values of a single pixel of a BitmapData object.
		public function setPixel32 (x:int, y:int, color:uint) : void;

		/// Converts a byte array into a rectangular region of pixel data.
		public function setPixels (rect:Rectangle, inputByteArray:ByteArray) : void;

		public function setVector (rect:Rectangle, inputVector:Vector.<uint>) : void;

		/// Tests pixel values in an image against a specified threshold and sets pixels that pass the test to new color values.
		public function threshold (sourceBitmapData:BitmapData, sourceRect:Rectangle, destPoint:Point, operation:String, threshold:uint, color:uint = 0, mask:uint = 4294967295, copySource:Boolean = false) : uint;

		/// Unlocks an image so that any objects that reference the BitmapData object, such as Bitmap objects, are updated when this BitmapData object changes.
		public function unlock (changeRect:Rectangle = null) : void;
	}
}
