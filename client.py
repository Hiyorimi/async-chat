#!/usr/bin/env python

from threading import Thread
import argparse
import ssl

import websocket
import tornado.escape


SERVER_URL = "%(protocol)s://%(host)s:%(port)s/chatsocket"


def format_message(message):
    return '\n{}\n> '.format(message)


def print_message(message):
    print(format_message(message), end='')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('username',
                        help='choose a username (John, Bob or Susan)')
    parser.add_argument('--host', default='localhost',
                        help='server url or ip')
    parser.add_argument('--port', default='8888',
                        help='server port')
    args = parser.parse_args()

    try:
        ws = websocket.create_connection(
            SERVER_URL % dict(
                protocol=('ws' if args.host == 'localhost' else 'wss'),
                host=args.host,
                port=args.port
            ),
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )
    except ConnectionRefusedError:
        print('Failed to connect to server')
        return

    ws.send(tornado.escape.json_encode(
        {'type': 'auth', 'username': args.username}))

    ###################################################################
    def receive():
        while True:
            try:
                message = ws.recv()
            except websocket._exceptions.WebSocketConnectionClosedException:
                print('Connection closed by server (press Enter to exit)')
                return

            print_message(message)

    # Start a receiver thread
    t = Thread(target=receive, daemon=True)
    t.start()
    ###################################################################

    # Prompt user for messages and send them to the server
    message = None
    while 1:
        message = input('> ')

        # Quit message received or server closed the connection and
        # receiver is dead
        if message == 'q' or not t.is_alive():
            ws.close()
            break

        if not message:
            print('Use q to close the client')
            continue

        ws.send(message)
    else:
        ws.close()


if __name__ == "__main__":
    main()
