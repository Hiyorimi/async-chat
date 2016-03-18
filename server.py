#!/usr/bin/env python

import logging
import json
import os

import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado import gen

from dao import DAO


PORT = 8888


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/chatsocket", ChatSocketHandler),
            (r"/login", AuthLoginHandler),
            (r"/logout", AuthLogoutHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/login",
            debug=True
        )
        super(Application, self).__init__(handlers, **settings)
        # Create a data access object for my application
        self.dao = DAO()


class HandlerMixin:

    @property
    def dao(self):
        return self.application.dao

    def get_current_user(self):
        user_id = self.get_cookie('async_chat_user')
        return self.dao.get_user(int(user_id)) if user_id else None


class MainHandler(HandlerMixin, tornado.web.RequestHandler):

    @tornado.web.authenticated
    def get(self):
        self.render('index.html')


class AuthLoginHandler(HandlerMixin, tornado.web.RequestHandler):

    def get(self):
        self.render('login.html', error=None)

    @gen.coroutine
    def post(self):
        user = self.dao.get_user(name=self.get_argument('username'))
        if user:
            self.set_cookie('async_chat_user', str(user['id']))
            self.redirect(self.get_argument('next', '/'))
        else:
            self.render('login.html', error='incorrect username')


class AuthLogoutHandler(HandlerMixin, tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie('async_chat_user')
        self.redirect(self.get_argument("next", "/login"))


class ChatSocketHandler(HandlerMixin, tornado.websocket.WebSocketHandler):
    error_messages = {
        'bad_type': tornado.escape.json_encode(
            {'type': 'error', 'message': 'bad message type'}),
        'bad_json': tornado.escape.json_encode(
            {'type': 'error', 'message': 'invalid json in message'}
        )
    }
    # Counter for ChatSocketHandler instances
    client_id = 0

    # {user_id: handler} mapping
    clients = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_types = {
            'get_user_list': self.on_get_user_list_msg,
            'get_online_user_list': self.on_get_online_user_list_msg,
            'message': self.on_message_msg
        }

    def open(self):
        ChatSocketHandler.client_id += 1
        # You can start three or less clients
        if ChatSocketHandler.client_id >= 4:
            self.close()
            return

        # First connected client gets the first user, second -- the second,
        # third -- the third.
        self.user = self.dao.get_user(ChatSocketHandler.client_id)
        # Register this handler
        ChatSocketHandler.clients[self.user['id']] = self

        self.write_message(tornado.escape.json_encode(
            {'type': 'connected',
             'id': self.user['id'],
             'name': self.user['name']}
        ))

    def on_close(self):
        try:
            # Remove this handler from register
            del ChatSocketHandler.clients[self.user['id']]
        except AttributeError:
            # Fourth client tried to connect, but we closed the connection,
            # so this handler has no user attribute attached
            pass

    def on_message(self, message):
        logging.info("GOT MESSAGE %r", message)

        # Help client to exit gracefully
        if message == 'exit':
            self.write_message('exit')

        try:
            parsed = tornado.escape.json_decode(message)
        except json.decoder.JSONDecodeError:
            self.write_error_message('bad_json')
            return

        message_type = parsed.get('type')
        if message_type not in self.api_types:
            self.write_error_message('bad_type')
            return

        # Call the right bound method for this message type
        self.api_types[message_type](parsed)

    def on_get_user_list_msg(self, parsed):
        users = self.dao.get_users()
        for u in users:
            u['status'] = (
                'online' if u['id'] in ChatSocketHandler.clients else 'offline'
            )
        response = tornado.escape.json_encode(users)
        self.write_message(response)

    def on_get_online_user_list_msg(self, parsed):
        online_users = [handler.user
                        for handler in ChatSocketHandler.clients.values()]
        for u in online_users:
            u['status'] = 'online'

        self.write_message(tornado.escape.json_encode(online_users))

    def on_message_msg(self, parsed):
        message = parsed['message']
        receiver_id = int(parsed['to'])
        time = parsed['time']

        self.dao.save_message(
            text=message,
            from_user=self.user['id'],
            to_user=receiver_id,
            time=time
        )
        status = (
            'online' if receiver_id in ChatSocketHandler.clients else 'offline'
        )

        receiver_message = tornado.escape.json_encode(
            {'type': 'message',
             'message': message,
             'from': self.user['id']}
        )
        response = tornado.escape.json_encode(
            {'type': 'status',
             'id': receiver_id,
             'status': status}
        )
        self.write_message(response)

        if status == 'offline':
            return

        ChatSocketHandler.clients[receiver_id].write_message(receiver_message)

    def write_error_message(self, error_type):
        error_message = self.error_messages[error_type]
        self.write_message(error_message)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(PORT)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
