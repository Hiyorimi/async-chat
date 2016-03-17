# async-chat
Python 3.5  
1. A simple python websocket client (one thread to send messages, another to receive)  
2. A websocket server built using Tornado

`pip install -r requirements.txt`  
`python server.py` in one terminal  
`python client.py` in other terminals  

Start the server, open another terminal and start the client. Receive a message with your id and name.  
Start another client and send one of the messsages, specified in `task.txt`  
You can connect only three times, after that you need to restart the server.
