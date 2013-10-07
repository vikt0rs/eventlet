import os

import eventlet
from eventlet import backdoor
from eventlet.green import socket
import tests


SOCKET_PATH = '/tmp/eventlet_backdoor_test.socket'


def silent_unlink(path):
    try:
        os.unlink(SOCKET_PATH)
    except OSError:
        pass


class BackdoorTest(tests.LimitedTestCase):
    def tearDown(self):
        silent_unlink(SOCKET_PATH)

    def test_server(self):
        listener = socket.socket()
        listener.bind(('localhost', 0))
        listener.listen(50)
        serv = eventlet.spawn(backdoor.backdoor_server, listener)
        client = socket.socket()
        client.connect(('localhost', listener.getsockname()[1]))
        f = client.makefile('rw')
        assert 'Python' in f.readline()
        f.readline()  # build info
        f.readline()  # help info
        assert 'InteractiveConsole' in f.readline()
        self.assertEqual('>>> ', f.read(4))
        f.write('print("hi")\n')
        f.flush()
        self.assertEqual('hi\n', f.readline())
        self.assertEqual('>>> ', f.read(4))
        f.close()
        client.close()
        serv.kill()
        # wait for the console to discover that it's dead
        eventlet.sleep(0.1)

    def test_server_on_ipv6(self):
        listener = socket.socket(socket.AF_INET6)
        listener.bind(('::1', 0))
        listener.listen(5)
        serv = eventlet.spawn(backdoor.backdoor_server, listener)
        client = socket.socket(socket.AF_INET6)
        client.connect(listener.getsockname())
        f = client.makefile('rw')
        self.assert_('Python' in f.readline())
        f.readline()  # build info
        f.readline()  # help info
        self.assert_('InteractiveConsole' in f.readline())
        self.assertEquals('>>> ', f.read(4))
        f.write('print("hi")\n')
        f.flush()
        self.assertEquals('hi\n', f.readline())
        self.assertEquals('>>> ', f.read(4))
        f.write('exit()\n')
        f.close()
        client.close()
        serv.kill()
        # wait for the console to discover that it's dead
        eventlet.sleep(0.1)

    def test_server_on_unix_socket(self):
        silent_unlink(SOCKET_PATH)
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(SOCKET_PATH)
        listener.listen(5)
        serv = eventlet.spawn(backdoor.backdoor_server, listener)
        client = socket.socket(socket.AF_UNIX)
        client.connect(SOCKET_PATH)
        f = client.makefile('rw')
        self.assert_('Python' in f.readline())
        f.readline()  # build info
        f.readline()  # help info
        self.assert_('InteractiveConsole' in f.readline())
        self.assertEquals('>>> ', f.read(4))
        f.write('print("hi")\n')
        f.flush()
        self.assertEquals('hi\n', f.readline())
        self.assertEquals('>>> ', f.read(4))
        f.write('exit()\n')
        f.close()
        client.close()
        serv.kill()
        # wait for the console to discover that it's dead
        eventlet.sleep(0.1)


if __name__ == '__main__':
    tests.main()
