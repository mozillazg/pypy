package
{
	/// The Date class represents date and time information.
	public class Date extends Object
	{
		public static const length : int;

		/// The day of the month (an integer from 1 to 31) specified by a Date object according to local time.
		public function get date () : Number;
		public function set date (value:Number) : void;

		/// The day of the month (an integer from 1 to 31) of a Date object according to universal time (UTC).
		public function get dateUTC () : Number;
		public function set dateUTC (value:Number) : void;

		/// The day of the week (0 for Sunday, 1 for Monday, and so on) specified by this Date according to local time.
		public function get day () : Number;

		/// The day of the week (0 for Sunday, 1 for Monday, and so on) of this Date  according to universal time (UTC).
		public function get dayUTC () : Number;

		/// The full year (a four-digit number, such as 2000) of a Date object according to local time.
		public function get fullYear () : Number;
		public function set fullYear (value:Number) : void;

		/// The four-digit year of a Date object according to universal time (UTC).
		public function get fullYearUTC () : Number;
		public function set fullYearUTC (value:Number) : void;

		/// The hour (an integer from 0 to 23) of the day portion of a Date object according to local time.
		public function get hours () : Number;
		public function set hours (value:Number) : void;

		/// The hour (an integer from 0 to 23) of the day of a Date object according to universal time (UTC).
		public function get hoursUTC () : Number;
		public function set hoursUTC (value:Number) : void;

		/// The milliseconds (an integer from 0 to 999) portion of a Date object according to local time.
		public function get milliseconds () : Number;
		public function set milliseconds (value:Number) : void;

		/// The milliseconds (an integer from 0 to 999) portion of a Date object according to universal time (UTC).
		public function get millisecondsUTC () : Number;
		public function set millisecondsUTC (value:Number) : void;

		/// The minutes (an integer from 0 to 59) portion of a Date object according to local time.
		public function get minutes () : Number;
		public function set minutes (value:Number) : void;

		/// The minutes (an integer from 0 to 59) portion of a Date object according to universal time (UTC).
		public function get minutesUTC () : Number;
		public function set minutesUTC (value:Number) : void;

		/// The month (0 for January, 1 for February, and so on) portion of a  Date object according to local time.
		public function get month () : Number;
		public function set month (value:Number) : void;

		/// The month (0 [January] to 11 [December]) portion of a Date object according to universal time (UTC).
		public function get monthUTC () : Number;
		public function set monthUTC (value:Number) : void;

		/// The seconds (an integer from 0 to 59) portion of a Date object according to local time.
		public function get seconds () : Number;
		public function set seconds (value:Number) : void;

		/// The seconds (an integer from 0 to 59) portion of a Date object according to universal time (UTC).
		public function get secondsUTC () : Number;
		public function set secondsUTC (value:Number) : void;

		/// The number of milliseconds since midnight January 1, 1970, universal time, for a Date object.
		public function get time () : Number;
		public function set time (value:Number) : void;

		/// The difference, in minutes, between universal time (UTC) and the computer's local time.
		public function get timezoneOffset () : Number;

		/// Constructs a new Date object that holds the specified date and time.
		public function Date (year:* = null, month:* = null, date:* = null, hours:* = null, minutes:* = null, seconds:* = null, ms:* = null);

		/// Returns the day of the month (an integer from 1 to 31) specified by a Date object according to local time.
		public function getDate () : Number;

		/// Returns the day of the week (0 for Sunday, 1 for Monday, and so on) specified by this Date according to local time.
		public function getDay () : Number;

		/// Returns the full year (a four-digit number, such as 2000) of a Date object according to local time.
		public function getFullYear () : Number;

		/// Returns the hour (an integer from 0 to 23) of the day portion of a Date object according to local time.
		public function getHours () : Number;

		/// Returns the milliseconds (an integer from 0 to 999) portion of a Date object according to local time.
		public function getMilliseconds () : Number;

		/// Returns the minutes (an integer from 0 to 59) portion of a Date object according to local time.
		public function getMinutes () : Number;

		/// Returns the month (0 for January, 1 for February, and so on) portion of this  Date according to local time.
		public function getMonth () : Number;

		/// Returns the seconds (an integer from 0 to 59) portion of a Date object according to local time.
		public function getSeconds () : Number;

		/// Returns the number of milliseconds since midnight January 1, 1970, universal time, for a Date object.
		public function getTime () : Number;

		/// Returns the difference, in minutes, between universal time (UTC) and the computer's local time.
		public function getTimezoneOffset () : Number;

		/// Returns the day of the month (an integer from 1 to 31) of a Date object, according to universal time (UTC).
		public function getUTCDate () : Number;

		/// Returns the day of the week (0 for Sunday, 1 for Monday, and so on) of this Date  according to universal time (UTC).
		public function getUTCDay () : Number;

		/// Returns the four-digit year of a Date object according to universal time (UTC).
		public function getUTCFullYear () : Number;

		/// Returns the hour (an integer from 0 to 23) of the day of a Date object according to universal time (UTC).
		public function getUTCHours () : Number;

		/// Returns the milliseconds (an integer from 0 to 999) portion of a Date object according to universal time (UTC).
		public function getUTCMilliseconds () : Number;

		/// Returns the minutes (an integer from 0 to 59) portion of a Date object according to universal time (UTC).
		public function getUTCMinutes () : Number;

		/// Returns the month (0 [January] to 11 [December]) portion of a Date object according to universal time (UTC).
		public function getUTCMonth () : Number;

		/// Returns the seconds (an integer from 0 to 59) portion of a Date object according to universal time (UTC).
		public function getUTCSeconds () : Number;

		/// Converts a string representing a date into a number equaling the number of milliseconds elapsed since January 1, 1970, UTC.
		public static function parse (s:*) : Number;

		/// Sets the day of the month, according to local time, and returns the new time in milliseconds.
		public function setDate (date:* = null) : Number;

		/// Sets the year, according to local time, and returns the new time in milliseconds.
		public function setFullYear (year:* = null, month:* = null, date:* = null) : Number;

		/// Sets the hour, according to local time, and returns the new time in milliseconds.
		public function setHours (hour:* = null, min:* = null, sec:* = null, ms:* = null) : Number;

		/// Sets the milliseconds, according to local time, and returns the new time in milliseconds.
		public function setMilliseconds (ms:* = null) : Number;

		/// Sets the minutes, according to local time, and returns the new time in milliseconds.
		public function setMinutes (min:* = null, sec:* = null, ms:* = null) : Number;

		/// Sets the month and optionally the day of the month, according to local time, and returns the new time in milliseconds.
		public function setMonth (month:* = null, date:* = null) : Number;

		/// Sets the seconds, according to local time, and returns the new time in milliseconds.
		public function setSeconds (sec:* = null, ms:* = null) : Number;

		/// Sets the date in milliseconds since midnight on January 1, 1970, and returns the new time in milliseconds.
		public function setTime (t:* = null) : Number;

		/// Sets the day of the month, in universal time (UTC), and returns the new time in milliseconds.
		public function setUTCDate (date:* = null) : Number;

		/// Sets the year, in universal time (UTC), and returns the new time in milliseconds.
		public function setUTCFullYear (year:* = null, month:* = null, date:* = null) : Number;

		/// Sets the hour, in universal time (UTC), and returns the new time in milliseconds.
		public function setUTCHours (hour:* = null, min:* = null, sec:* = null, ms:* = null) : Number;

		/// Sets the milliseconds, in universal time (UTC), and returns the new time in milliseconds.
		public function setUTCMilliseconds (ms:* = null) : Number;

		/// Sets the minutes, in universal time (UTC), and returns the new time in milliseconds.
		public function setUTCMinutes (min:* = null, sec:* = null, ms:* = null) : Number;

		/// Sets the month, and optionally the day, in universal time(UTC) and returns the new time in milliseconds.
		public function setUTCMonth (month:* = null, date:* = null) : Number;

		/// Sets the seconds, and optionally the milliseconds, in universal time (UTC) and returns the new time in milliseconds.
		public function setUTCSeconds (sec:* = null, ms:* = null) : Number;

		/// Returns a string representation of the day and date only, and does not include the time or timezone.
		public function toDateString () : String;

		/// Returns a String representation of the day and date only, and does not include the time or timezone.
		public function toLocaleDateString () : String;

		/// Returns a String representation of the day, date, time, given in local time.
		public function toLocaleString () : String;

		/// Returns a String representation of the time only, and does not include the day, date, year, or timezone.
		public function toLocaleTimeString () : String;

		/// Returns a String representation of the day, date, time, and timezone.
		public function toString () : String;

		/// Returns a String representation of the time and timezone only, and does not include the day and date.
		public function toTimeString () : String;

		/// Returns a String representation of the day, date, and time in universal time (UTC).
		public function toUTCString () : String;

		/// Returns the number of milliseconds between midnight on January 1, 1970, universal time, and the time specified in the parameters.
		public static function UTC (year:*, month:*, date:* = 1, hours:* = 0, minutes:* = 0, seconds:* = 0, ms:* = 0, ...rest) : Number;

		/// Returns the number of milliseconds since midnight January 1, 1970, universal time, for a Date object.
		public function valueOf () : Number;
	}
}
