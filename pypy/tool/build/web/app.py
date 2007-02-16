#!/usr/bin/env python

""" a web server that displays status info of the meta server and builds """

import py
import time
from pypy.tool.build import config
from pypy.tool.build import execnetconference
from pypy.tool.build.build import BuildRequest
from pypy.tool.build.web.server import HTTPError, Resource, Collection, \
                                       Handler, FsFile

from templess import templess

mypath = py.magic.autopath().dirpath()

def fix_html(html):
    return ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
            '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n%s' % (
            html.strip().encode('UTF-8'),))

class IndexPage(Resource):
    """ the index page """
    def handle(self, handler, path, query):
        template = templess.template(
            mypath.join('templates/index.html').read())
        return ({'Content-Type': 'text/html; charset=UTF-8'},
                fix_html(template.unicode({})))

class ServerPage(Resource):
    """ base class for pages that communicate with the server
    """

    def __init__(self, config, gateway=None):
        self.config = config
        self.gateway = gateway or self.init_gateway()

    remote_code = """
        import sys
        sys.path += %r

        from pypy.tool.build import metaserver_instance
        ret = metaserver_instance.%s(%s)
        channel.send(ret)
        channel.close()
    """

    def call_method(self, methodname, args=''):
        """ calls a method on the server
        
            methodname is the name of the method to call, args is a string
            which is _interpolated_ into the method call (so if you want to
            pass the integers 1 and 2 as arguments, 'args' will become '1, 2')
        """
        conference = execnetconference.conference(self.gateway,
                                                  self.config.port, False)
        channel = conference.remote_exec(self.remote_code % (self.config.path,
                                                             methodname,
                                                             args))
        ret = channel.receive()
        channel.close()
        return ret

    def init_gateway(self):
        if self.config.server in ['localhost', '127.0.0.1']:
            gw = py.execnet.PopenGateway()
        else:
            gw = py.execnet.SshGateway(self.config.server)
        return gw

class ServerStatusPage(ServerPage):
    """ a page displaying overall meta server statistics """

    def handle(self, handler, path, query):
        template = templess.template(
            mypath.join('templates/serverstatus.html').read())
        return ({'Content-Type': 'text/html; charset=UTF-8'},
                fix_html(template.unicode(self.get_status())))

    def get_status(self):
        return self.call_method('status')

class BuildersInfoPage(ServerPage):
    def handle(self, handler, path, query):
        template = templess.template(
            mypath.join('templates/buildersinfo.html').read())
        return ({'Content-Type': 'text/html; charset=UTF-8'},
                fix_html(template.unicode({'builders':
                                           self.get_buildersinfo()})))

    def get_buildersinfo(self):
        infos = self.call_method('buildersinfo')
        # some massaging of the data for Templess
        for binfo in infos:
            binfo['sysinfo'] = [binfo['sysinfo']]
            if binfo['busy_on']:
                b = binfo['busy_on']
                d = BuildRequest.fromstring(binfo['busy_on']).todict()
                d.pop('sysinfo', None) # same as builder
                d.pop('build_end_time', None) # it's still busy ;)
                # templess doesn't understand dicts this way...
                d['compileinfo'] = [{'key': k, 'value': v} for (k, v) in
                                    d['compileinfo'].items()]
                for key in ['request_time', 'build_start_time']:
                    if d[key]:
                        d[key] = time.strftime('%Y/%m/%d %H:%M:%S',
                                               time.gmtime(d[key]))
                binfo['busy_on'] = [d]
        return infos

class BuildPage(ServerPage):
    """ display information for one build """

    def __init__(self, buildid, config, gateway=None):
        super(BuildPage, self).__init__(config, gateway)
        self._buildid = buildid

    def handle(self, handler, path, query):
        pass

class BuildsIndexPage(ServerPage):
    """ display the list of available builds """

    def handle(self, handler, path, query):
        template = templess.template(
            mypath.join('templates/builds.html').read())
        return ({'Content-Type': 'text/html; charset=UTF-8'},
                fix_html(template.unicode({'builds': self.get_builds()})))

    def get_builds(self):
        return []

class Builds(Collection):
    """ container for BuildsIndexPage and BuildPage """

    def __init__(self, config, gateway=None):
        self.index = BuildsIndexPage(config, gateway)
        self.config = config
        self.gateway = gateway
    
    def traverse(self, path, orgpath):
        """ generate a BuildPage on the fly """
        # next element of the path is the id of the build '/<collection>/<id>'
        name = path.pop()
        if name in ['', 'index']:
            return self.index
        if len(path):
            # no Collection type children here...
            raise HTTPError(404)
        # we have a name for a build, let's build a page for it (if it can't
        # be found, this page will raise an exception)
        return BuildPage(name, self.config, self.gateway)

class Application(Collection):
    """ the application root """
    index = IndexPage()
    style = FsFile(mypath.join('theme/style.css'), 'text/css')
    serverstatus = ServerStatusPage(config)
    buildersinfo = BuildersInfoPage(config)
    builds = Builds(config)

class AppHandler(Handler):
    application = Application()

if __name__ == '__main__':
    from pypy.tool.build.web.server import run_server
    run_server(('', 8080), AppHandler)

