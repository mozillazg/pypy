package flash.xml
{
	/// The XMLNodeType class contains constants used with XMLNode.nodeType.
	public class XMLNodeType extends Object
	{
		public static const CDATA_NODE : uint;
		public static const COMMENT_NODE : uint;
		public static const DOCUMENT_TYPE_NODE : uint;
		/// Specifies that the node is an element.
		public static const ELEMENT_NODE : uint;
		public static const PROCESSING_INSTRUCTION_NODE : uint;
		/// Specifies that the node is a text node.
		public static const TEXT_NODE : uint;
		public static const XML_DECLARATION : uint;

		public function XMLNodeType ();
	}
}
