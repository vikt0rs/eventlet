from __future__ import print_function

from code import InteractiveConsole
import errno
import socket
import sys
import traceback

import eventlet
from eventlet import hubs
from eventlet.support import greenlets, get_errno

try:
    sys.ps1
except AttributeError:
    sys.ps1 = '>>> '
try:
    sys.ps2
except AttributeError:
    sys.ps2 = '... '


class FileProxy(object):
    def __init__(self, f):
        self.f = f

    def isatty(self):
        return True

    def flush(self):
        pass

    def write(self, data, *a, **kw):
        self.f.write(data, *a, **kw)
        self.f.flush()

    def readline(self, *a):
        return self.f.readline(*a).replace('\r\n', '\n')

    def __getattr__(self, attr):
        return getattr(self.f, attr)


def format_addr(a):
    if len(a) >= 2:
        # IP
        return '{0}:{1}'.format(*a)
    if len(a) == 1:
        # UNIX socket / named pipe
        return str(a[0])
    # unknown
    return str(a)


class SocketConsole(greenlets.greenlet):
    def __init__(self, desc, hostport, init_locals):
        self.hostport = hostport
        self.init_locals = init_locals
        # mangle the socket
        self.desc = FileProxy(desc)
        greenlets.greenlet.__init__(self)
        # place to store exception if InteractiveConsole terminates
        self.exc_info = None

    def run(self):
        try:
            console = InteractiveConsole(self.init_locals)
            console.interact()
        except SystemExit:
            pass
        except BaseException:
            self.exc_info = sys.exc_info()
        finally:
            self.switch_out()
            self.finalize()

    def switch(self, *args, **kw):
        self.saved = sys.stdin, sys.stderr, sys.stdout
        sys.stdin = sys.stdout = sys.stderr = self.desc
        greenlets.greenlet.switch(self, *args, **kw)

    def switch_out(self):
        sys.stdin, sys.stderr, sys.stdout = self.saved

    def finalize(self):
        # restore the state of the socket
        self.desc = None
        print("backdoor closed to {0}".format(format_addr(self.hostport)))

        if self.exc_info is not None:
            traceback.print_exception(*self.exc_info)


def backdoor_server(sock, init_locals=None):
    """ Blocking function that runs a backdoor server on the socket *sock*,
    accepting connections and running backdoor consoles for each client that
    connects.

    The *init_locals* argument is a dictionary that will be included in the locals()
    of the interpreters.  It can be convenient to stick important application
    variables in here.
    """
    print("backdoor server listening on {0}".format(format_addr(sock.getsockname())))
    try:
        try:
            while True:
                socketpair = sock.accept()
                backdoor(socketpair, init_locals)
        except socket.error as e:
            # Broken pipe means it was shutdown
            if get_errno(e) != errno.EPIPE:
                raise
    finally:
        sock.close()


def backdoor(conn_info, init_locals=None):
    """Sets up an interactive console on a socket with a single connected
    client.  This does not block the caller, as it spawns a new greenlet to
    handle the console.  This is meant to be called from within an accept loop
    (such as backdoor_server).
    """
    conn, addr = conn_info
    print("backdoor to {0}".format(format_addr(addr)))
    fl = conn.makefile("rw")
    console = SocketConsole(fl, addr, init_locals)
    hub = hubs.get_hub()
    hub.schedule_call_global(0, console.switch)


if __name__ == '__main__':
    backdoor_server(eventlet.listen(('127.0.0.1', 9000)), {})
