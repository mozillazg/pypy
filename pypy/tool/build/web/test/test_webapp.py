import py
from py.__.test.web.webcheck import check_html
from pypy.tool.build.web.webapp import *
from pypy.tool.build.web.conftest import option
from pypy.tool.build.test import fake
from pypy.tool.build import config as build_config

TESTPORT = build_config.testport

here = py.magic.autopath().dirpath()
pypyparent = here.dirpath().dirpath().dirpath().dirpath().dirpath()

def html_validate(html):
    if not option.webcheck:
        py.test.skip('Skipping XHTML validation (rest of the test passed)')
    check_html(html)

class TestTemplate(object):
    def test_render(self):
        # XXX stupid test ;) but perhaps we're going to add features later or
        # something...
        s = py.std.StringIO.StringIO('<foo>%(foo)s</foo>')
        s.seek(0)
        t = Template(s)
        assert t.render({'foo': 'bar'}) == '<foo>bar</foo>'

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

    from pypy.tool.build.web.test.test_webapp import FakeMetaServer
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
    def test_handle(self):
        p = IndexPage()
        headers, html = p.handle(None, '/', '')
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

    def test_handle(self):
        server_channel.send(('set_status', {'builders': 3, 'running': 2,
                                            'done': 7, 'waiting': 5,
                                            'queued': 2}))
        p = ServerStatusPage(config, gateway)
        headers, html = p.handle(None, '/serverstatus', '')
        assert headers == {'Content-Type': 'text/html; charset=UTF-8'}
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuilderInfoPage(object):
    def test_get_builderinfo(self):
        p = BuildersInfoPage(config, gateway)
        assert p.get_buildersinfo() == []
        server_channel.send(('set_buildersinfo', [{'foo': 'bar'}]))
        assert p.get_buildersinfo() == [{'foo': 'bar'}]

    def test_handle(self):
        server_channel.send(('set_buildersinfo', [{'hostname': 'host1',
                                                   'sysinfo': {'foo': 'bar'},
                                                   'busy_on': None},
                                                  {'hostname': 'host2',
                                                   'sysinfo': {'foo': 'baz'},
                                                   'busy_on': {'spam': 'eggs'},
                                                   }]))
        p = BuildersInfoPage(config, gateway)
        headers, html = p.handle(None, '/buildersinfo', '')
        assert headers == {'Content-Type': 'text/html; charset=UTF-8'}
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuildPage(object):
    def test_handle(self):
        pass

class TestBuildCollectionIndexPage(object):
    def test_get_builds(self):
        pass

    def test_handle(self):
        p = BuildCollectionIndexPage(config, gateway)
        headers, html = p.handle(None, '/builds/', '')
        assert headers == {'Content-Type': 'text/html; charset=UTF-8'}
        assert html.strip().startswith('<!DOCTYPE html')
        assert html.strip().endswith('</html>')
        html_validate(html)

class TestBuildCollection(object):
    def test_traverse(self):
        p = BuildCollection(config, gateway)
        assert p.traverse(['index'], '/builds/index') is p.index
        assert p.traverse([''], '/builds/') is p.index
        assert isinstance(p.traverse(['foo'], '/builds/foo'), BuildPage)
        py.test.raises(HTTPError,
                       "p.traverse(['foo', 'bar'], '/builds/foo/bar')")

