from BaseHTTPServer import HTTPServer as BaseHTTPServer, BaseHTTPRequestHandler
import py
from os   import system
from cgi  import parse_qs
from sys  import platform
from time import sleep
import webbrowser
from pypy.translator.avm.log import log
log = log.browsertest

class HTTPServer(BaseHTTPServer):
    allow_reuse_address = True

class config:
    http_port = 10001

    html_page = """<html>
<head>
<title>PyPy AVM1 Test Case: %s</title>
</head>
<body onload="runTest()">
<object type="application/x-shockwave-flash" data="testcase.swf" width="400" height="300">
<param name="movie" value="test.swf" />
</object>
</body>
</html>"""

    crossdomain_xml="""<cross-domain-policy>
<allow-access-from domain="*" secure="false"/>
</cross-domain-policy>"""
    
class TestCase(object):
    def __init__(self, name, swfdata):
        self.testcasename = name
        self.swfdata = swfdata
        self.result = None
    
class TestHandler(BaseHTTPRequestHandler):
    """The HTTP handler class that provides the tests and handles results"""

    def do_GET(self):
        global do_status
        if self.path == "/test.html":
            data = config.html_page % testcase.xtestcasename
            mime = 'text/html'
        elif self.path == "/test.swf":
            data = testcase.swfdata
            mime = 'application/x-shockwave-flash'
        elif self.path == "/crossdomain.xml":
            data = config.crossdomain_xml
            mime = 'text/xml'
        self.serve_data(mime, data)
        do_status = 'do_GET'

    def do_POST(self):
        global do_status
        if self.path == "/test.result":
            form = parse_qs(self.rfile.read(int(self.headers['content-length'])))
            testcase.result = form['result'][0]
        do_status = 'do_POST'

    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)


class BrowserTest(object):
    """The browser driver"""

    def start_server(self, port, html_page, is_interactive):
        server_address = ('', port)
        self.httpd = HTTPServer(server_address, TestHandler)
        self.httpd.is_interactive = is_interactive
        self.httpd.html_page = html_page

    def get_result(self):
        global do_status
        do_status = None
        while do_status != 'do_GET':
            self.httpd.handle_request()
        while do_status != 'do_POST':
            self.httpd.handle_request()
        return jstest.result


def browsertest(testcase, swfdata):
    global driver, testcase
    testcase = TestCase(str(testcase), str(swfdata))
    driver = BrowserTest()
    driver.start_server(config.http_port, html_page, is_interactive)
        webbrowser.open('http://localhost:%d/test.html' % config.http_port)

    result = driver.get_result()
    return result
