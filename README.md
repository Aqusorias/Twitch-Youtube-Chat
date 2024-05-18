# Twitch-Chat
To run the code you will need to install Python.  
Additionally, you will need to install the following python module using pip:  

python -m pip install keyboard  

Once Python is set up, simply change the Stream Link & the Streamer in ChatListener_Settings.py, and you'll be ready to go.
Just run the "ChatListener_Settings.py" file and it should work!

### Information

I couldn't really get the messages and usernames from Youtube to work correctly, due to Youtube formatting weirdly.
So if somebody sends an emoji, it could either be a (?) or very many confusing characters if it's a channel-emoji (uc8rcebzjsletkf_-agpm20g/ewiizn72gs-l_9epj4ugoaq).
Also, if a user has non-ASCII characters, f.e. "あ" or "♡", they will be converted into a (?).

That doesn't apply to Twitch Chat.