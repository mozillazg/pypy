from pypy.translator.gensupp import NameManager
#from pypy.translator.js.optimize import is_optimized_function

class AVM1NameManager(NameManager):
    def __init__(self, db):
        NameManager.__init__(self)
        self.db = db
        self.reserved = {}


        # Source:
        # http://livedocs.adobe.com/flash/8/main/wwhelp/wwhimpl/common/html/wwhelp.htm?context=LiveDocs_Parts&file=00001236.html
        reserved_words = '''add and break case catch class continue default
        delete do dynamic else eq extends finally for function ge get gt if
        ifFrameLoaded implements import in instanceof interface intrinsic
        le lt ne new not on onClipEvent or private public return setw
        static switch tellTarget this throw try typeof var void while with'''
        
        for name in reserved_words.split():
            self.reserved[name] = True
            
        predefined_classes_and_objects = '''
    Accessibility Accordion Alert Array Binding Boolean Button Camera
    CellRenderer CheckBox Collection Color ComboBox ComponentMixins ContextMenu
    ContextMenuItem CustomActions CustomFormatterCustomValidator DataGrid
    DataHolder DataProvider DataSet DataType Date DateChooser DateField Delta
    DeltaItem DeltaPacket DepthManager EndPoint Error FocusManager Form Function
    Iterator Key Label List Loader LoadVars LocalConnection Log Math Media Menu
    MenuBar Microphone Mouse MovieClip MovieClipLoader NetConnection NetStream
    Number NumericStepper Object PendingCall PopUpManager PrintJob ProgressBar
    RadioButton RDBMSResolver Screen ScrollPane Selection SharedObject Slide SOAPCall
    Sound Stage String StyleManager System TextArea TextField TextFormat TextInput
    TextSnapshot TransferObject Tree TreeDataProvider TypedValue UIComponent
    UIEventDispatcher UIObject Video WebService WebServiceConnector Window XML
    XMLConnector XUpdateResolver'''
        
        for name in predefined_classes_and_objects.split():
            self.reserved[name] = True
        
        self.make_reserved_names(' '.join(self.reserved))
        
        self.predefined = set(predefined_classes_and_objects)

    #def uniquename(self, name, lenmax=0):
    #    return NameManager.uniquename(self, , lenmax)

    def ensure_non_reserved(self, name):
        while name in self.reserved:
            name += '_'
        return name
