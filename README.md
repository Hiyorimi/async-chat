# async-chat
Python 3.5  
A simple chat on websockets, built using Tornado.

`pip install -r requirements.txt`  
`python server.py` in one terminal  
`localhost:8888` in your browser 

There are only three users: John, Bob and Susan.
Valid messages are in `task.txt`

You can also use a console client:  
`python client.py <username>`  
You can use browser and console client to chat with each other.  
Any valid user can have multiple connections open and chat with other users.
