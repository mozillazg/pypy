package authoring
{
	import authoring.authObject;
	import flash.geom.Rectangle;
	import flash.geom.ColorTransform;
	import flash.geom.Point;
	import flash.geom.Matrix3D;
	import flash.geom.Matrix;

	public class authObject extends Object
	{
		public function get FirstChild () : authObject;

		public function get Key () : uint;

		public function get NextSibling () : authObject;

		public static function get offScreenSurfaceRenderingEnabled () : Boolean;
		public static function set offScreenSurfaceRenderingEnabled (value:Boolean) : void;

		public function get SwfKey () : uint;

		public function get Type () : uint;

		public function authObject (key:uint);

		public function BlendingMode () : String;

		public function Bounds (flags:uint, minFrame:int = -16000, maxFrame:int = 16000) : Rectangle;

		public function CacheAsBitmap () : Boolean;

		public function CenterPoint () : Point;

		public function ColorXForm () : ColorTransform;

		public function EndPosition () : int;

		public function Filters () : Array;

		public function FrameForFrameNumber (frameNum:int) : authObject;

		public function FrameOffset () : int;

		public function FrameType () : uint;

		public function HasEmptyPath () : Boolean;

		public function HasShapeSelection () : Boolean;

		public function IsFloater () : Boolean;

		public function IsPrimitive () : Boolean;

		public function IsSelected () : Boolean;

		public function IsVisible (inThumbnailPreview:Boolean) : Boolean;

		public function LivePreviewSize () : Point;

		public function Locked () : Boolean;

		public function MotionPath () : authObject;

		public function ObjMatrix () : Matrix;

		public function OutlineColor () : uint;

		public function OutlineMode () : Boolean;

		public function RegistrationPoint () : Point;

		public function Scale9Grid () : Rectangle;

		public function StartPosition () : int;

		public function SymbolBehavior () : int;

		public function SymbolMode () : int;

		public function ThreeDMatrix () : Matrix3D;

		public function ThreeDTranslationHandlePoints () : Array;
	}
}
