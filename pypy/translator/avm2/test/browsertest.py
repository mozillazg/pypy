from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from cgi import parse_qs

import time
import webbrowser

class config(object):
    http_port = 10001

    html_page = """<html>
<head>
<title>PyPy AVM2 Backend Test Case: %s</title>
</head>
<body>
<object type="application/x-shockwave-flash" data="test.swf" width="%d" height="%d">
<param name="movie" value="test.swf" />
<param name="allowScriptAccess" value="always" />
</object>
</body>
</html>"""

    crossdomain_xml="""<cross-domain-policy>
<allow-access-from domain="*" secure="false"/>
</cross-domain-policy>"""

class InstanceWrapper(Exception):
    def __init__(self, class_name):
        self.class_name = class_name

class ExceptionWrapper(Exception):
    def __init__(self, class_name):
        self.class_name = class_name

    def __repr__(self):
        return 'ExceptionWrapper(%r)' % (self.class_name,)

class TestCase(object):
    def __init__(self, name, swfdata):
        self.name = name
        self.swfdata = swfdata
        self.result = None
    
class TestHandler(BaseHTTPRequestHandler):
    """The HTTP handler class that provides the tests and handles results"""

    def do_GET(self):
        testcase = self.server.testcase
        if self.path == "/test.html":
            data = config.html_page % (testcase.name, testcase.swfdata.width, testcase.swfdata.height)
            mime = 'text/html'
        elif self.path == "/test.swf":
            data = testcase.swfdata.serialize()
            mime = 'application/x-shockwave-flash'
        elif self.path == "/crossdomain.xml":
            data = config.crossdomain_xml
            mime = 'text/xml'
        self.serve_data(mime, data)

    def do_POST(self):
        if self.path == "/test.result":
            form = parse_qs(self.rfile.read(int(self.headers['content-length'])))
            self.server.testcase.result = form['result'][0]

    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)

class BrowserTest(object):
    """The browser driver"""

    def start_server(self, port, testcase):
        server_address = ('', port)
        self.httpd = HTTPServer(server_address, TestHandler)
        self.httpd.testcase = testcase

    def get_result(self):
        testcase = self.httpd.testcase
        while testcase.result is None:
            self.httpd.handle_request()
        return testcase.result

def browsertest(name, swfdata):
    testcase = TestCase(str(name), swfdata)
    driver = BrowserTest()
    driver.start_server(config.http_port, testcase)
    webbrowser.open('http://localhost:%d/test.html' % config.http_port)
    
    return driver.get_result()
