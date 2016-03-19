#!/usr/bin/env python

import logging
import json
import os

import tornado.escape
from tornado import gen
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from collections import defaultdict

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

    def post(self):
        # Pony needs non-empty string, so I pass 'username' in case of
        # empty string in the form's username input
        name = self.get_argument('username') or 'username'
        user = self.dao.get_user(name=name)
        if user:
            self.set_cookie('async_chat_user', str(user.id))
            self.redirect(self.get_argument('next', '/'))
        else:
            users = self.dao.get_users()
            assert len(users) == 3, 'Users were not created in DAO __init__'

            usernames = (', '.join(u.name for u in users[:-1]) +
                         ' or ' + users[-1].name)
            self.render('login.html',
                        error='incorrect username (use {})'.format(usernames))


class AuthLogoutHandler(tornado.web.RequestHandler):

    def get(self):
        self.clear_cookie('async_chat_user')
        self.redirect(self.get_argument("next", "/login"))


class ChatSocketHandler(HandlerMixin, tornado.websocket.WebSocketHandler):
    server_messages = {
        'bad_type': tornado.escape.json_encode(
            {'type': 'error', 'message': 'bad message type'}),
        'bad_json': tornado.escape.json_encode(
            {'type': 'error', 'message': 'invalid json object in message'}),
        'bad_username': tornado.escape.json_encode(
            {'type': 'error', 'message': 'bad username'}),
        'bad_message': tornado.escape.json_encode(
            {'type': 'error', 'message': 'bad message for this type'}
        )
    }
    # {user_id: {handler1, handler2..}} mapping
    clients = defaultdict(set)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_types = {
            'get_user_list': self.on_get_user_list_msg,
            'get_online_user_list': self.on_get_online_user_list_msg,
            'message': self.on_message_msg,
            'auth': self.on_auth_msg
        }

    def open(self):
        if not self.current_user:
            # Console client connected, see authentication in `on_auth_msg`
            return

        self.register_client(self.current_user)
        self.write_connected_message()

    def on_close(self):
        if not self.current_user:
            return

        handlers_set = ChatSocketHandler.clients[self.current_user.id]
        handlers_set.discard(self)
        if not handlers_set:
            # remove this user_id from clients register
            del ChatSocketHandler.clients[self.current_user.id]

    def on_message(self, message):
        logging.info("GOT MESSAGE %r", message)

        try:
            parsed = tornado.escape.json_decode(message)
        except json.decoder.JSONDecodeError:
            self.write_error_message('bad_json')
            return

        if not isinstance(parsed, dict):
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
            u.status = (
                'online' if u.id in ChatSocketHandler.clients else 'offline'
            )
        response = tornado.escape.json_encode(users)
        self.write_message(response)

    def on_get_online_user_list_msg(self, parsed):
        # There may be multiple handlers for a user, but I only need one item in
        # the list of online users for a user, so I build this help dict
        help_dict = {
            h.current_user.id: h.current_user
            for handler_set in ChatSocketHandler.clients.values()
            for h in handler_set
        }
        online_users = list(help_dict.values())
        for u in online_users:
            u.status = 'online'

        self.write_message(tornado.escape.json_encode(online_users))

    @gen.coroutine
    def on_auth_msg(self, parsed):
        # Pony needs non-empty string to look up users by name
        username = parsed.get('username', 'username')
        user = self.dao.get_user(name=username)
        if not user:
            # Wait for self.write_error_message() to finish before closing
            # the socket
            yield self.write_error_message('bad_username')
            self.close()
        else:
            # Handler needs this attribute in its other methods
            self.current_user = user
            self.register_client(user)
            self.write_connected_message()

    def register_client(self, user):
        ChatSocketHandler.clients[user.id].add(self)

    def on_message_msg(self, parsed):
        message = parsed.get('message')
        try:
            receiver_id = int(parsed.get('to'))
        except (ValueError, TypeError):
            receiver_id = None

        time = parsed.get('time')

        if not all([message, receiver_id, time]):
            self.write_error_message('bad_message')
            return

        self.dao.save_message(
            text=message,
            from_user=self.current_user.id,
            to_user=receiver_id,
            time=time
        )
        status = (
            'online' if receiver_id in ChatSocketHandler.clients else 'offline'
        )

        receiver_message = tornado.escape.json_encode(
            {'type': 'message',
             'message': message,
             'from': self.current_user.id}
        )
        response = tornado.escape.json_encode(
            {'type': 'status',
             'id': receiver_id,
             'status': status}
        )
        self.write_message(response)

        if status == 'offline':
            return

        for handler in ChatSocketHandler.clients[receiver_id]:
            handler.write_message(receiver_message)

    @gen.coroutine
    def write_error_message(self, error_type):
        error_message = self.server_messages[error_type]
        yield self.write_message(error_message)

    def write_connected_message(self):
        self.write_message(tornado.escape.json_encode(
            {'type': 'connected',
             'id': self.current_user.id,
             'name': self.current_user.name}
        ))


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(PORT)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
