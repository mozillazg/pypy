package
{
	/// The Array class lets you access and manipulate arrays.
	public class Array extends Object
	{
		/// Specifies case-insensitive sorting for the Array class sorting methods.
		public static const CASEINSENSITIVE : uint;
		/// Specifies descending sorting for the Array class sorting methods.
		public static const DESCENDING : uint;
		/// A non-negative integer specifying the number of elements in the array.
		public static const length : int;
		/// Specifies numeric (instead of character-string) sorting for the Array class sorting methods.
		public static const NUMERIC : uint;
		/// Specifies that a sort returns an array that consists of array indices.
		public static const RETURNINDEXEDARRAY : uint;
		/// Specifies the unique sorting requirement for the Array class sorting methods.
		public static const UNIQUESORT : uint;

		public function get length () : uint;
		public function set length (newLength:uint) : void;

		/// Lets you create an array that contains the specified elements.
		public function Array (...rest);

		/// Concatenates the elements specified in the parameters.
		public function concat (...rest) : Array;

		/// Executes a test function on each item in the array until an item is reached that returns false for the specified function.
		public function every (callback:Function, thisObject:* = null) : Boolean;

		/// Executes a test function on each item in the array and constructs a new array for all items that return true for the specified function.
		public function filter (callback:Function, thisObject:* = null) : Array;

		/// Executes a function on each item in the array.
		public function forEach (callback:Function, thisObject:* = null) : void;

		/// Searches for an item in an array by using strict equality (===) and returns the index position of the item.
		public function indexOf (searchElement:*, fromIndex:* = 0) : int;

		/// Converts the elements in an array to strings.
		public function join (sep:* = null) : String;

		/// Searches for an item in an array, working backward from the last item, and returns the index position of the matching item using strict equality (===).
		public function lastIndexOf (searchElement:*, fromIndex:* = 2147483647) : int;

		/// Executes a function on each item in an array, and constructs a new array of items corresponding to the results of the function on each item in the original array.
		public function map (callback:Function, thisObject:* = null) : Array;

		/// Removes the last element from an array and returns the value of that element.
		public function pop () : *;

		/// Adds one or more elements to the end of an array and returns the new length of the array.
		public function push (...rest) : uint;

		/// Reverses the array in place.
		public function reverse () : Array;

		/// Removes the first element from an array and returns that element.
		public function shift () : *;

		/// Returns a new array that consists of a range of elements from the original array.
		public function slice (startIndex:* = 0, endIndex:* = 16777215) : Array;

		/// Executes a test function on each item in the array until an item is reached that returns true.
		public function some (callback:Function, thisObject:* = null) : Boolean;

		/// Sorts the elements in an array.
		public function sort (...rest) : *;

		/// Sorts the elements in an array according to one or more fields in the array.
		public function sortOn (names:*, options:* = null) : *;

		/// Adds elements to and removes elements from an array.
		public function splice (startIndex:int, deleteCount:uint, ...rest) : *;

		/// Adds one or more elements to the beginning of an array and returns the new length of the array.
		public function unshift (...rest) : uint;
	}
}
