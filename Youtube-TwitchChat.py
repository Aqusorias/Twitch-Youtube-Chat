import requests
import re
import time
import json
import concurrent.futures
from colorama import Fore, init
import traceback
import socket
import random



init(autoreset=True)

class Twitch:
    re_prog = None
    sock = None
    partial = b''
    login_ok = False
    channel = ''
    login_timestamp = 0

    def twitch_connect(self, channel):
        if self.sock: 
            self.sock.close()
        self.sock = None
        self.partial = b''
        self.login_ok = False
        self.channel = channel

        self.re_prog = re.compile(b'^(?::(?:([^ !\r\n]+)![^ \r\n]*|[^ \r\n]*) )?([^ \r\n]+)(?: ([^:\r\n]*))?(?: :([^\r\n]*))?\r\n', re.MULTILINE)

        print(Fore.CYAN + 'Connecting to Twitch...')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect(('irc.chat.twitch.tv', 6667))

        user = 'justinfan%i' % random.randint(10000, 99999)
        print(Fore.GREEN + 'Successfully connected to Twitch.')
        print(Fore.CYAN + 'Logging in anonymously as ' + Fore.BLUE + user + Fore.GREEN + ' ...')
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
                print(Fore.RED + 'Connection closed by Twitch. Reconnecting in 5 seconds...')
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

    def twitch_receive_messages(self):
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
                print(Fore.GREEN + 'Successfully logged in.')
                print(Fore.CYAN + 'Joining channel ' + Fore.BLUE + "%s." % self.channel)
                self.sock.send(('JOIN #%s\r\n' % self.channel).encode())
                self.login_ok = True
            elif cmd == 'JOIN':
                print(Fore.GREEN + 'Successfully joined channel ' + Fore.BLUE + '%s' % irc_message['params'][0].lstrip('#'))
                print(' ')

        if not self.login_ok:
            if time.time() - self.login_timestamp > 10:
                print(Fore.RED + 'No response from Twitch. Reconnecting...')
                self.reconnect(0)
                return []

        return privmsgs




class YouTube:
    session = None
    config = {}
    payload = {}

    thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    fetch_job = None
    next_fetch_time = 0

    re_initial_data = re.compile('(?:window\\s*\\[\\s*[\\"\']ytInitialData[\\"\']\\s*\\]|ytInitialData)\\s*=\\s*({.+?})\\s*;')
    re_config = re.compile('(?:ytcfg\\s*.set)\\(({.+?})\\)\\s*;')

    def get_continuation_token(self, data):
        cont = data['continuationContents']['liveChatContinuation']['continuations'][0]
        if 'timedContinuationData' in cont:
            return cont['timedContinuationData']['continuation']
        else:
            return cont['invalidationContinuationData']['continuation']

    def reconnect(self, delay):
        if self.fetch_job and self.fetch_job.running():
            if not self.fetch_job.cancel():
                print(Fore.CYAN + "Waiting for fetch job to finish...")
                self.fetch_job.result()
        print(Fore.CYAN + f"Retrying in {delay}...")
        if self.session: self.session.close()
        self.session = None
        self.config = {}
        self.payload = {}
        self.fetch_job = None
        self.next_fetch_time = 0
        time.sleep(delay)
        self.youtube_connect(self.channel_id, self.stream_url)

    def youtube_connect(self, channel_id, stream_url=None):
        print(Fore.CYAN + "Connecting to YouTube...")

        self.channel_id = channel_id
        self.stream_url = stream_url

        # Create http client session
        self.session = requests.Session()
        # Spoof user agent so yt thinks we're an upstanding browser
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
        # Add consent cookie to bypass google's consent page
        requests.utils.add_dict_to_cookiejar(self.session.cookies, {'CONSENT': 'YES+'})

        # Connect using stream_url if provided, otherwise use the channel_id
        if stream_url is not None:
            live_url = self.stream_url
        else:
            live_url = f"https://www.youtube.com/{self.channel_id}/live"
            time.sleep(2)

        res = self.session.get(live_url)
        if res.status_code == 404:
            live_url = f"https://www.youtube.com/{self.channel_id}/live"
            res = self.session.get(live_url)
        if not res.ok:
            if stream_url is not None:
                print(Fore.RED + f"Couldn't load the stream URL ({res.status_code} {res.reason}). Is the stream URL correct? {self.stream_url}")
            else:
                print(Fore.RED + f"Couldn't load livestream page ({res.status_code} {res.reason}). Is the channel ID correct? {self.channel_id}")
            time.sleep(5)
            exit(1)
        livestream_page = res.text

        # Find initial data in livestream page
        matches = list(self.re_initial_data.finditer(livestream_page))
        if len(matches) == 0:
            print(Fore.RED + "Couldn't find initial data in livestream page")
            time.sleep(5)
            exit(1)
        initial_data = json.loads(matches[0].group(1))


        # Get continuation token for live chat iframe
        iframe_continuation = None
        try:
            iframe_continuation = initial_data['contents']['twoColumnWatchNextResults']['conversationBar']['liveChatRenderer']['header']['liveChatHeaderRenderer']['viewSelector']['sortFilterSubMenuRenderer']['subMenuItems'][1]['continuation']['reloadContinuationData']['continuation']
        except Exception as e:
            print(Fore.RED + f"Couldn't find the livestream chat. Is the channel not live? url: {live_url}")
            time.sleep(5)
            exit(1)

        # Fetch live chat page
        res = self.session.get(f'https://youtube.com/live_chat?continuation={iframe_continuation}')
        if not res.ok:
            print(Fore.RED + f"Couldn't load live chat page ({res.status_code} {res.reason})")
            time.sleep(5)
            exit(1)
        live_chat_page = res.text

        # Find initial data in live chat page
        matches = list(self.re_initial_data.finditer(live_chat_page))
        if len(matches) == 0:
            print(Fore.RED + "Couldn't find initial data in live chat page")
            time.sleep(5)
            exit(1)
        initial_data = json.loads(matches[0].group(1))

        # Find config data
        matches = list(self.re_config.finditer(live_chat_page))
        if len(matches) == 0:
            print(Fore.RED + "Couldn't find config data in live chat page")
            time.sleep(5)
            exit(1)
        self.config = json.loads(matches[0].group(1))

        # Create payload object for making live chat requests
        token = self.get_continuation_token(initial_data)
        self.payload = {
            "context": self.config['INNERTUBE_CONTEXT'],
            "continuation": token,
            "webClientInfo": {
                "isDocumentHidden": False
            },
        }
        print(Fore.Green + "Connected.")
        print(' ')

    def fetch_messages(self):
        payload_bytes = bytes(json.dumps(self.payload), "utf8")
        res = self.session.post(f"https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key={self.config['INNERTUBE_API_KEY']}&prettyPrint=false", payload_bytes)
        if not res.ok:
            print(Fore.RED + f"Failed to fetch messages. {res.status_code} {res.reason}")
            print("Body:", res.text)
            print("Payload:", payload_bytes)
            self.session.close()
            self.session = None
            return []
        try:
            data = json.loads(res.text)
            self.payload['continuation'] = self.get_continuation_token(data)
            cont = data['continuationContents']['liveChatContinuation']
            messages = []
            if 'actions' in cont:
                for action in cont['actions']:
                    if 'addChatItemAction' in action:
                        if 'item' in action['addChatItemAction']:
                            if 'liveChatTextMessageRenderer' in action['addChatItemAction']['item']:
                                item = action['addChatItemAction']['item']['liveChatTextMessageRenderer']
                                messages.append({
                                    'author': item['authorName']['simpleText'],
                                    'content': item['message']['runs']
                                })
            return messages
        except Exception as e:
            print(Fore.RED + f"Failed to parse messages.")
            print("Body:", res.text)
            traceback.print_exc()
        return []

    def receive_messages(self):
        if self.session == None:
            self.reconnect(0)
        messages = []
        if not self.fetch_job:
            time.sleep(1.0/60.0)
            if time.time() > self.next_fetch_time:
                self.fetch_job = self.thread_pool.submit(self.fetch_messages)
        else:
            res = []
            timed_out = False
            try:
                res = self.fetch_job.result(1.0/60.0)
            except concurrent.futures.TimeoutError:
                timed_out = True
            except Exception:
                traceback.print_exc()
                self.session.close()
                self.session = None
                return
            if not timed_out:
                self.fetch_job = None
                self.next_fetch_time = time.time() + 10
            for item in res:
                msg = {
                    'username': item['author'],
                    'message': ''
                }
                for part in item['content']:
                    if 'text' in part:
                        msg['message'] += part['text']
                    elif 'emoji' in part:
                        msg['message'] += part['emoji']['emojiId']
                messages.append(msg)
        return messages
