package flash.text.engine
{
	/// The BreakOpportunity class is an enumeration of constant values that you can use to set the breakOpportunity property of the ElementFormat class.
	public class BreakOpportunity extends Object
	{
		/// Treats all characters in the ContentElement object as mandatory line break opportunities.
		public static const ALL : String;
		/// Treats any character in the ContentElement object as a line break opportunity.
		public static const ANY : String;
		/// Bases line break opportunities on Unicode character properties.
		public static const AUTO : String;
		/// Treats no characters in the ContentElement object as line break opportunities.
		public static const NONE : String;

		public function BreakOpportunity ();
	}
}
