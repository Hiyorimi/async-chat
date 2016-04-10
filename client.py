#!/usr/bin/env python

from threading import Thread
import argparse
import ssl
import contextlib

import websocket
import tornado.escape


SERVER_URL = "{protocol}://{host}:{port}/chatsocket"
QUIT = 'q'
PROMPT = '> '


@contextlib.contextmanager
def socket(ws):
    try:
        yield ws
    finally:
        ws.close()


def format_message(message):
    return '\n{}\n{}'.format(message, PROMPT)


def print_message(message):
    print(format_message(message), end='')


def receive(ws):
    while True:
        try:
            message = ws.recv()
        except websocket._exceptions.WebSocketConnectionClosedException:
            return

        print_message(message)


def parse_cli_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'username', help='choose a username (John, Bob or Susan)'
    )
    parser.add_argument(
        '--host', default='localhost',
        help='server url or ip (heroku url is "async-chat.herokuapp.com")'
    )
    parser.add_argument(
        '--port', default='8888',
        help=('server port (use 443 to connect to the server, '
              'deployed on heroku)')
    )
    return parser.parse_args()


def main(args):
    try:
        ws = websocket.create_connection(
            SERVER_URL.format(
                protocol=('ws' if args.host == 'localhost' else 'wss'),
                host=args.host,
                port=args.port
            ),
            # Don't validate ssl certificates
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )
    except ConnectionRefusedError:
        print('Failed to connect to server')
        return

    t = Thread(target=receive, args=(ws,), daemon=True)
    t.start()

    with socket(ws) as ws:
        ws.send(tornado.escape.json_encode(
            {'type': 'auth', 'username': args.username}))

        # Prompt user for messages and send them to the server
        message = None

        while 1:
            message = input(PROMPT)

            # Quit message received or server closed the connection and
            # receiver is dead
            if message == QUIT or not t.is_alive():
                break

            if not message:
                print('Use {} to close the client'.format(QUIT))
                continue

            ws.send(message)


if __name__ == "__main__":
    main(parse_cli_arguments())
