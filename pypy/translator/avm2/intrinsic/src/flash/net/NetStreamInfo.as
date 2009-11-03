package flash.net
{
	/// The NetStreamInfo class specifies the various Quality of Service (QOS) statistics related to a NetStream object and the underlying streaming buffer for audio, video, and data.
	public class NetStreamInfo extends Object
	{
		/// Provides the NetStream audio buffer size in bytes.
		public function get audioBufferByteLength () : Number;

		/// Provides NetStream audio buffer size in seconds.
		public function get audioBufferLength () : Number;

		/// Specifies the total number of audio bytes that have arrived in the queue, regardless of how many have been played or flushed.
		public function get audioByteCount () : Number;

		/// Specifies the rate at which the NetStream audio buffer is filled in bytes per second.
		public function get audioBytesPerSecond () : Number;

		/// Specifies the audio loss for the NetStream session.
		public function get audioLossRate () : Number;

		/// Specifies the total number of bytes that have arrived into the queue, regardless of how many have been played or flushed.
		public function get byteCount () : Number;

		/// Specifies the rate at which the NetStream buffer is filled in bytes per second.
		public function get currentBytesPerSecond () : Number;

		/// Provides the NetStream data buffer size in bytes.
		public function get dataBufferByteLength () : Number;

		/// Provides NetStream data buffer size in seconds.
		public function get dataBufferLength () : Number;

		/// Specifies the total number of bytes of data messages that have arrived in the queue, regardless of how many have been played or flushed.
		public function get dataByteCount () : Number;

		/// Specifies the rate at which the NetStream data buffer is filled in bytes per second.
		public function get dataBytesPerSecond () : Number;

		/// Returns the number of video frames dropped in the current NetStream playback session.
		public function get droppedFrames () : Number;

		/// Specifies the maximum rate at which the NetStream buffer is filled in bytes per second.
		public function get maxBytesPerSecond () : Number;

		/// Returns the stream playback rate in bytes per second.
		public function get playbackBytesPerSecond () : Number;

		/// Specifies the Smooth Round Trip Time for the NetStream session.
		public function get SRTT () : Number;

		/// Provides the NetStream video buffer size in bytes.
		public function get videoBufferByteLength () : Number;

		/// Provides NetStream video buffer size in seconds.
		public function get videoBufferLength () : Number;

		/// Specifies the total number of video bytes that have arrived in the queue, regardless of how many have been played or flushed.
		public function get videoByteCount () : Number;

		/// Specifies the rate at which the NetStream video buffer is filled in bytes per second.
		public function get videoBytesPerSecond () : Number;

		/// For internal use only; not recommended for use.
		public function NetStreamInfo (curBPS:Number, byteCount:Number, maxBPS:Number, audioBPS:Number, audioByteCount:Number, videoBPS:Number, videoByteCount:Number, dataBPS:Number, dataByteCount:Number, playbackBPS:Number, droppedFrames:Number, audioBufferByteLength:Number, videoBufferByteLength:Number, dataBufferByteLength:Number, audioBufferLength:Number, videoBufferLength:Number, dataBufferLength:Number, srtt:Number, audioLossRate:Number);

		/// Returns a text value listing the properties of this NetStreamInfo object.
		public function toString () : String;
	}
}
