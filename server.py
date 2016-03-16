#!/usr/bin/env python

import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=True
        )
        super(Application, self).__init__(handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", messages=ChatSocketHandler.cache)


class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    message_types = [
        'get_user_list',
        # 'get_online_user_list',
        'message'
    ]
    error_message = tornado.escape.json_encode(
        {'type': 'error', 'message': 'bad message type'})

    client_id = 0
    clients = {}

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        ChatSocketHandler.client_id += 1
        self.id = ChatSocketHandler.client_id
        ChatSocketHandler.clients[self.id] = self

    def on_close(self):
        self.clients.pop(self.id)

    def on_message(self, message):
        logging.info("got message %r", message)
        parsed = tornado.escape.json_decode(message)
        self.respond(parsed)

    def respond(self, parsed):
        message_type = parsed.get('type')
        if message_type not in self.message_types:
            self.write_error_message()
            return

        getattr(self, message_type)(parsed)

    def get_user_list(self, parsed):
        response = tornado.escape.json_encode(
            [{'id': id, 'status': 'online'}
             for id in self.clients.keys()]
        )
        self.write_message(response)

    def message(self, parsed):
        message = parsed['message']
        receiver_id = int(parsed['to'])
        # time = parsed['time']

        receiver_message = tornado.escape.json_encode(
            {'type': 'message',
             'message': message,
             'from': self.id}
        )
        response = tornado.escape.json_encode(
            {'type': 'status',
             'id': receiver_id,
             'status': 'online'}
        )
        self.write_message(response)
        ChatSocketHandler.clients[receiver_id].write_message(receiver_message)

    def write_error_message(self):
        self.write_message(self.error_message)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
