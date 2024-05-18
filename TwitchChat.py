import socket
import re
import random
import time

class Twitch:
    re_prog = None
    sock = None
    partial = b''
    login_ok = False
    channel = ''
    login_timestamp = 0

    def twitch_connect(self, channel):
        if self.sock: self.sock.close()
        self.sock = None
        self.partial = b''
        self.login_ok = False
        self.channel = channel

        self.re_prog = re.compile(b'^(?::(?:([^ !\r\n]+)![^ \r\n]*|[^ \r\n]*) )?([^ \r\n]+)(?: ([^:\r\n]*))?(?: :([^\r\n]*))?\r\n', re.MULTILINE)

        print('Connecting to Twitch...')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect(('irc.chat.twitch.tv', 6667))

        user = 'justinfan%i' % random.randint(10000, 99999)
        print('Connected to Twitch. Logging in anonymously as ' + user + ' ...')
        self.sock.send(('PASS asdf\r\nNICK %s\r\n' % user).encode())

        self.sock.settimeout(1.0/60.0)

        self.login_timestamp = time.time()

    def reconnect(self, delay):
        time.sleep(delay)
        self.twitch_connect(self.channel)

    def receive_and_parse_data(self):
        buffer = b''
        while True:
            received = b''
            try:
                received = self.sock.recv(4096)
            except socket.timeout:
                break
            if not received:
                print('Connection closed by Twitch. Reconnecting in 5 seconds...')
                self.reconnect(5)
                return []
            buffer += received

        if buffer:
            if self.partial:
                buffer = self.partial + buffer
                self.partial = []

            res = []
            matches = list(self.re_prog.finditer(buffer))
            for match in matches:
                res.append({
                    'name':     (match.group(1) or b'').decode(errors='replace'),
                    'command':  (match.group(2) or b'').decode(errors='replace'),
                    'params':   list(map(lambda p: p.decode(errors='replace'), (match.group(3) or b'').split(b' '))),
                    'trailing': (match.group(4) or b'').decode(errors='replace'),
                })

            if not matches:
                self.partial += buffer
            else:
                end = matches[-1].end()
                if end < len(buffer):
                    self.partial = buffer[end:]

            return res

        return []

    def receive_messages(self):
        privmsgs = []
        for irc_message in self.receive_and_parse_data():
            cmd = irc_message['command']
            if cmd == 'PRIVMSG':
                privmsgs.append({
                    'username': irc_message['name'],
                    'message': irc_message['trailing'],
                })
            elif cmd == 'PING':
                self.sock.send(b'PONG :tmi.twitch.tv\r\n')
            elif cmd == '001':
                print('Successfully logged in. Joining channel %s.' % self.channel)
                self.sock.send(('JOIN #%s\r\n' % self.channel).encode())
                self.login_ok = True
            elif cmd == 'JOIN':
                print('Successfully joined channel %s' % irc_message['params'][0])

        if not self.login_ok:
            if time.time() - self.login_timestamp > 10:
                print('No response from Twitch. Reconnecting...')
                self.reconnect(0)
                return []

        return privmsgs