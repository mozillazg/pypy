import py
from py.__.test.web.webcheck import check_html
from pypy.tool.build.web.app import *
from pypy.tool.build.web.conftest import option
from pypy.tool.build.test import fake
from pypy.tool.build import config as build_config
from pypy.tool.build import build

TESTPORT = build_config.testport

here = py.magic.autopath().dirpath()
pypyparent = here.dirpath().dirpath().dirpath().dirpath().dirpath()

def html_validate(html):
    if not option.webcheck:
        py.test.skip('Skipping XHTML validation (rest of the test passed)')
    check_html(html)

class FakeMetaServer(object):
    def __init__(self):
        self._status = {}
        self._builders = []

    def status(self):
        return self._status

    def buildersinfo(self):
        return self._builders

_metaserver_init = """
    import sys
    sys.path += %r

    from pypy.tool.build.web.test.test_app import FakeMetaServer
    from pypy.tool import build
    build.metaserver_instance = s = FakeMetaServer()
    try:
        while 1:
            command = channel.receive()
            if command == 'quit':
                break
            command, data = command
            if command == 'set_status':
                s._status = data
            elif command == 'set_buildersinfo':
                s._builders = data
    finally:
        channel.close()
"""

def init_fake_metaserver(port, path):
    gw = py.execnet.PopenGateway()
    conference = execnetconference.conference(gw, port, True)
    channel = conference.remote_exec(_metaserver_init % (path,))
    return channel

def setup_module(mod):
    mod.path = path = pypyparent.strpath
    mod.server_channel = init_fake_metaserver(TESTPORT, path)
    mod.config = fake.Container(port=TESTPORT, path=path)
    mod.gateway = py.execnet.PopenGateway()

def teardown_module(mod):
    mod.server_channel.send('quit')
    mod.gateway.exit()

class TestIndexPage(object):
    def test_call(self):
        a = Application()
        headers, html = a.index(None, '/', '')
        assert headers == {'Content-Type': 'text/html; charset=UTF-8'}
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestServerStatusPage(object):
    def test_get_status(self):
        p = ServerStatusPage(config, gateway)
        assert p.get_status() == {}
        server_channel.send(('set_status', {'foo': 'bar'}))
        assert p.get_status() == {'foo': 'bar'}

    def test_call(self):
        server_channel.send(('set_status', {'builders': 3, 'running': 2,
                                            'done': 7, 'waiting': 5,
                                            'queued': 2}))
        p = ServerStatusPage(config, gateway)
        headers, html = p(None, '/serverstatus', '')
        assert headers == {'Content-Type': 'text/html; charset=UTF-8'}
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuilderInfoPage(object):
    def test_get_builderinfo(self):
        p = BuildersInfoPage(config, gateway)
        assert p.get_buildersinfo() == []
        server_channel.send(('set_buildersinfo', [{'sysinfo': 'foo',
                                                   'busy_on': None}]))
        assert p.get_buildersinfo() == [{'sysinfo': ['foo'], 'busy_on': None}]

    def test_call(self):
        b = build.BuildRequest('foo@bar.com', {}, {'foo': 'bar'},
                               'http://codespeak.net/svn/pypy/dist', 10, 2,
                               123456789)
        busy_on = b.serialize()
        server_channel.send(('set_buildersinfo', [{'hostname': 'host1',
                                                   'sysinfo': {
                                                    'os': 'linux2',
                                                    'maxint':
                                                     9223372036854775807,
                                                    'byteorder': 'little'},
                                                   'busy_on': None},
                                                  {'hostname': 'host2',
                                                   'sysinfo': {
                                                    'os': 'zx81',
                                                    'maxint': 255,
                                                    'byteorder': 'little'},
                                                   'busy_on': busy_on,
                                                   }]))
        p = BuildersInfoPage(config, gateway)
        headers, html = p(None, '/buildersinfo', '')
        assert headers == {'Content-Type': 'text/html; charset=UTF-8'}
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuildPage(object):
    def test_call(self):
        pass

class TestBuildsIndexPage(object):
    def test_get_builds(self):
        pass

    def test_call(self):
        p = BuildsIndexPage(config, gateway)
        headers, html = p(None, '/builds/', '')
        assert headers == {'Content-Type': 'text/html; charset=UTF-8'}
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuilds(object):
    def test_traverse(self):
        p = Builds(config, gateway)
        assert p.traverse(['index'], '/builds/index') is p.index
        assert p.traverse([''], '/builds/') is p.index
        assert isinstance(p.traverse(['foo'], '/builds/foo'), BuildPage)
        py.test.raises(HTTPError,
                       "p.traverse(['foo', 'bar'], '/builds/foo/bar')")

