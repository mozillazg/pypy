package flash.media
{
	import flash.events.EventDispatcher;
	import flash.utils.ByteArray;
	import flash.net.URLRequest;
	import flash.media.SoundLoaderContext;
	import flash.media.SoundChannel;
	import flash.media.SoundTransform;
	import flash.media.ID3Info;

	/**
	 * Dispatched when data is received as a load operation progresses.
	 * @eventType flash.events.ProgressEvent.PROGRESS
	 */
	[Event(name="progress", type="flash.events.ProgressEvent")] 

	/**
	 * Dispatched when a load operation starts.
	 * @eventType flash.events.Event.OPEN
	 */
	[Event(name="open", type="flash.events.Event")] 

	/**
	 * Dispatched when an input/output error occurs that causes a load operation to fail.
	 * @eventType flash.events.IOErrorEvent.IO_ERROR
	 */
	[Event(name="ioError", type="flash.events.IOErrorEvent")] 

	/**
	 * Dispatched by a Sound object when ID3 data is available for an MP3 sound.
	 * @eventType flash.events.Event.ID3
	 */
	[Event(name="id3", type="flash.events.Event")] 

	/**
	 * Dispatched when data has loaded successfully.
	 * @eventType flash.events.Event.COMPLETE
	 */
	[Event(name="complete", type="flash.events.Event")] 

	/**
	 * Dispatched when the player requests new audio data.
	 * @eventType flash.events.SampleDataEvent.SAMPLE_DATA
	 */
	[Event(name="sampleData", type="flash.events.SampleDataEvent")] 

	/// The Sound class lets you work with sound in an application.
	public class Sound extends EventDispatcher
	{
		/// Returns the currently available number of bytes in this sound object.
		public function get bytesLoaded () : uint;

		/// Returns the total number of bytes in this sound object.
		public function get bytesTotal () : int;

		/// Provides access to the metadata that is part of an MP3 file.
		public function get id3 () : ID3Info;

		/// Returns the buffering state of external MP3 files.
		public function get isBuffering () : Boolean;

		/// The length of the current sound in milliseconds.
		public function get length () : Number;

		/// The URL from which this sound was loaded.
		public function get url () : String;

		/// Closes the stream, causing any download of data to cease.
		public function close () : void;

		/// Extracts raw sound data from a Sound object.
		public function extract (target:ByteArray, length:Number, startPosition:Number = -1) : Number;

		/// Initiates loading of an external MP3 file from the specified URL.
		public function load (stream:URLRequest, context:SoundLoaderContext = null) : void;

		/// Generates a new SoundChannel object to play back the sound.
		public function play (startTime:Number = 0, loops:int = 0, sndTransform:SoundTransform = null) : SoundChannel;

		/// Creates a new Sound object.
		public function Sound (stream:URLRequest = null, context:SoundLoaderContext = null);
	}
}
