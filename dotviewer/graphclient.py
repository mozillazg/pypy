import os, sys, re
import msgstruct

this_dir = os.path.dirname(os.path.abspath(__file__))
GRAPHSERVER = os.path.join(this_dir, 'graphserver.py')


def display_dot_file(dotfile, wait=True):
    """ Display the given dot file in a subprocess.
    """
    if not os.path.exists(dotfile):
        raise IOError("No such file: %s" % (dotfile,))
    import graphpage
    page = graphpage.DotFileGraphPage(str(dotfile))
    display_page(page, wait=wait)

def display_page(page, wait=True):
    messages = [(msgstruct.CMSG_INIT, msgstruct.MAGIC)]
    history = [page]
    pagecache = {}

    def getpage(graph_id):
        page = history[graph_id]
        try:
            return pagecache[page]
        except KeyError:
            result = page.content()
            pagecache.clear()    # a cache of a single entry should be enough
            pagecache[page] = result
            return result

    def reload(graph_id):
        page = getpage(graph_id)
        messages.extend(page_messages(page, graph_id))
        send_graph_messages(io, messages)
        del messages[:]

    io = spawn_handler()
    reload(0)

    if wait:
        try:
            while True:
                msg = io.recvmsg()
                # handle server-side messages
                if msg[0] == msgstruct.MSG_RELOAD:
                    graph_id = msg[1]
                    pagecache.clear()
                    reload(graph_id)
                elif msg[0] == msgstruct.MSG_FOLLOW_LINK:
                    graph_id = msg[1]
                    word = msg[2]
                    page = getpage(graph_id)
                    try:
                        page = page.followlink(word)
                    except KeyError:
                        io.sendmsg(msgstruct.CMSG_MISSING_LINK)
                    else:
                        # when following a link from an older page, assume that
                        # we can drop the more recent history
                        graph_id += 1
                        history[graph_id:] = [page]
                        reload(graph_id)
        except EOFError:
            pass
        io.close()

def page_messages(page, graph_id):
    import graphparse
    return graphparse.parse_dot(graph_id, page.source, page.links)

def send_graph_messages(io, messages):
    ioerror = None
    for msg in messages:
        try:
            io.sendmsg(*msg)
        except IOError, ioerror:
            break
    # wait for MSG_OK or MSG_ERROR
    try:
        while True:
            msg = io.recvmsg()
            if msg[0] == msgstruct.MSG_OK:
                break
    except EOFError:
        ioerror = ioerror or IOError("connexion unexpectedly closed "
                                     "(graphserver crash?)")
    if ioerror is not None:
        raise ioerror

def spawn_handler():
    gsvar = os.environ.get('GRAPHSERVER')
    if not gsvar:
        return spawn_local_handler()
    else:
        try:
            host, port = gsvar.split(':')
            host = host or '127.0.0.1'
            port = int(port)
        except ValueError:
            raise ValueError("$GRAPHSERVER must be set to HOST:PORT, got %r" %
                             (gvvar,))
        import socket
        s = socket.socket()
        s.connect((host, port))
        return msgstruct.SocketIO(s)

def spawn_local_handler():
    cmdline = '"%s" -u "%s" --stdio' % (sys.executable, GRAPHSERVER)
    child_in, child_out = os.popen2(cmdline, 'tb', 0)
    io = msgstruct.FileIO(child_out, child_in)
    return io
