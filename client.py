#!/usr/bin/env python

# TODO: try to use higher level websocket API next time
from threading import Thread

import websocket


SERVER_URL = "ws://127.0.0.1:8888/chatsocket"


def format_message(message):
    return '\n{}\n> '.format(message)


def print_message(message):
    print(format_message(message), end='')


def main():
    try:
        ws = websocket.create_connection(SERVER_URL)
    except ConnectionRefusedError:
        print('Failed to connect to server')
        return

    ###################################################################
    def receive():
        while True:
            try:
                message = ws.recv()
            except websocket._exceptions.WebSocketConnectionClosedException:
                return

            if message == 'exit':
                return

            print_message(message)

    # Start a receiver thread
    t = Thread(target=receive)
    t.start()
    ###################################################################

    # Prompt user for messages and send them to the server
    message = None
    while message != 'exit':
        message = input('> ')

        # There has been no 'exit' message and receiver is dead, so the server
        # has closed the connection
        if not t.is_alive():
            print('Connection closed by server')
            break

        if not message:
            print('Use "exit" to close the client')
            continue

        ws.send(message)
    else:
        # 'exit' message has been input so wait for the receiver to die
        t.join()
        ws.close()


if __name__ == "__main__":
    main()
