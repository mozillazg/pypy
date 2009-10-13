package adobe.utils
{
	/// Lets you issue Flash JavaScript API (JSAPI) commands from ActionScript.
	public function MMExecute (name:String) : String;

	/// [FP10] Notifies an application hosting a SWF command that a command is done and instructs the application to commit or discard the changes submitted by the MMExecute() command.
	public function MMEndCommand (endStatus:Boolean, notifyString:String) : void;

}

