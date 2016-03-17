import json
import sys
import websocket
import tornado.escape

from threading import Thread


if __name__ == "__main__":

    ws = websocket.create_connection("ws://127.0.0.1:8888/chatsocket")

    def receive():
        while True:
            try:
                message = ws.recv()
            except websocket._exceptions.WebSocketConnectionClosedException:
                print('Connection closed by server')
                sys.exit()

            try:
                print('\n', tornado.escape.json_decode(message), end='\n> ')
            except json.decoder.JSONDecodeError:
                print('\n', 'Invalid json message received\n> ')

    Thread(target=receive).start()

    while True:
        message = input('> ')
        if not message:
            break

        # ws.send(tornado.escape.json_encode(message))
        ws.send(message)

    ws.close()
