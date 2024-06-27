import concurrent.futures
import time
from colorama import Fore, Back, Style, init 
import sys
import keyboard         # killswitch
import Youtube-TwitchChat


# Replace this with your Twitch username, if you have problems, try using the username in lowercase
TWITCH_CHANNEL = 'AqusoriasYuki' 


# Replace this with your Youtube's Channel ID
# Find this by going to the Home page of your Youtube Channel and looking at the URL:
# https://www.youtube.com/channel/UCu50dqKnCp06ZsEXrVndWQg -> Channel ID is "UCu50dqKnCp06ZsEXrVndWQg"
# https://www.youtube.com/@LofiGirl -> Channel ID is "@LofiGirl"

# CURRENTLY NOT WORKING, JUST LEAVE IT EMPTY; NOBODY CARES
YOUTUBE_CHANNEL_ID = ""


# Normally if you have the YOUTUBE_CHANNEL_ID you could just have it as "None", but that's bugged currently.
# So just put in the Streams URL in quotes.
# If it's not bugged, only put in the stream Link, if you test it as a unlisted stream.
YOUTUBE_STREAM_URL = ("https://www.youtube.com/watch?v=4oStw0r33so")


# The lower the message, the faster the messages are processed: it's the number of seconds it will take to handle all messages in the queue.
# Twitch delivers messages in batches, if set to 0 it will process it instantly, that's pretty bad if you have many messages incoming.
# So if you don't have many messages, just leave it on 0.2.
MESSAGE_RATE = 0.2

# If you have a lot of messages, you can for example put in 10, so it will only process the first 10 messages of the queue/batch.
# This won't be a problem if you aren't getting a lot of messages, so just leave it on 50.
MAX_QUEUE_LENGTH = 50




last_time = time.time()
message_queue = []
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count())
active_tasks = []

# Countdown before the bot starts
countdown = 2
print(' ')
if countdown != 0:
    print('Starting countdown ...')
    while countdown > 0:
        print(countdown)
        countdown -= 1
        time.sleep(1)
    print(' ')



twitch_chat = Youtube-TwitchChat.Twitch()
twitch_chat.twitch_connect(TWITCH_CHANNEL)

youtube_chat = Youtube-TwitchChat.YouTube()
youtube_chat.youtube_connect(YOUTUBE_CHANNEL_ID, YOUTUBE_STREAM_URL)


# Read README.md for more information about the messages / usernames.

# Remember that the Username isn't lowercase and sometimes contains Emojis or f.e. JPN Characters (?).
# If you want to do something with the Username, use for .strip() to remove the (?) and make it lowercase.
def handle_message(message, source):
    try:
        msg = message['message']
        username = message['username']

        msg = msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
        username = username.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)

        print(f"{source} - {username}: {msg}")
            

########################################## Add Rules ##########################################




        # If you use msg.lower(), it will ignore the case of the message.


        # If the message is exactly "hello"
        if msg.lower() == "hello":
            print(Fore.MAGENTA + "User said Hello")

        # If message contains the word "hello"
        if "hello" in msg.lower():
            print(Fore.MAGENTA + "User said Hello")
            
            



##################################### <-  ›   ⏑.⏑   ‹  -> #####################################
    except Exception as exception:
        print(Fore.RED + "Encountered exception: " + Fore.YELLOW + str(exception))


while True:
    active_tasks = [twitch_chat for twitch_chat in active_tasks if not twitch_chat.done()]
    active_tasks2 = [youtube_chat for youtube_chat in active_tasks if not youtube_chat.done()]

    # Check for new messages
    new_messages = twitch_chat.receive_messages();
    if new_messages:
        message_queue += [(message, 'Twitch') for message in new_messages]  # Add source identifier
        message_queue = message_queue[-MAX_QUEUE_LENGTH:] # Shorten the queue to only the most recent X messages
        
    new_messages2 = youtube_chat.receive_messages();
    if new_messages2:
        message_queue += [(message, 'YouTube') for message in new_messages2]  # Add source identifier
        message_queue = message_queue[-MAX_QUEUE_LENGTH:] # Shorten the queue to only the most recent X messages

    messages_to_handle = []
    if not message_queue: # No messages in the queue
        last_time = time.time()
    else:
        # Determine how many messages it should handle now
        msg_rate = 1 if MESSAGE_RATE == 0 else (time.time() - last_time) / MESSAGE_RATE # If MESSAGE_RATE is 0, it will process all messages instantly (1), else it will process them in the time specified
        msg_to_handle = int(msg_rate * len(message_queue))
        if msg_to_handle > 0:
            # Removes the messages from the queue that it handled
            messages_to_handle = message_queue[0:msg_to_handle]
            del message_queue[0:msg_to_handle]
            last_time = time.time();

        
    if not messages_to_handle:
        continue
    else:
        for message, source in messages_to_handle:  # Pass source to handle_message
            if len(active_tasks) <= os.cpu_count():
                active_tasks.append(thread_pool.submit(handle_message, message, source))  # Pass source
            else:
                print(Back.YELLOW + Fore.RED + Style.BRIGHT + f'WARNING: active tasks ({len(active_tasks)}) exceeds number of workers ({os.cpu_count()}). ({len(message_queue)} messages in the queue)')
                 
 
 
    # If User presses Shift+Backspace, automatically end the program - Killswitch
    if keyboard.is_pressed('shift+backspace'):
        
        print(' ')
        print('\033[1m' + Back.YELLOW + Fore.RED + 'Program ended by user' + '\033[0m')
        print(' ')
        exit()
