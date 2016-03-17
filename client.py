import sys
from threading import Thread

import websocket


if __name__ == "__main__":

    ws = websocket.create_connection("ws://127.0.0.1:8888/chatsocket")

    def format_message(message):
        return '\n{}\n> '.format(message)

    def print_message(message):
        print(format_message(message), end='')

    def receive():
        while True:
            try:
                message = ws.recv()
            except websocket._exceptions.WebSocketConnectionClosedException:
                print('Connection closed by server')
                sys.exit()

            if message == 'exit':
                break

            print_message(message)

    t = Thread(target=receive)
    t.start()

    while True:
        message = input('> ')
        if not message:
            print('Use "exit" to close the client')
            continue

        ws.send(message)
        if message == 'exit':
            break

    # Wait for thread-receiver to finish
    t.join()
    ws.close()
