import os

from pony import orm
from tornado.util import ObjectDict


# All data retrieving methods return dicts because of the way
# Pony orm works (see db_session decorator explanation).
class DAO:
    '''
    Data access object -- handles interactions with the database.
    '''
    def __init__(self, db_name='async_chat_db.sqlite'):
        try:
            os.remove(db_name)
        except FileNotFoundError:
            pass

        self.db = orm.Database()
        self.db.bind('sqlite', db_name, create_db=True)
        self.define_entities()
        self.db.generate_mapping(create_tables=True)
        self.create_users()

    def define_entities(self):

        class User(self.db.Entity):
            from_messages = orm.Set('Message', reverse='from_user')
            to_messages = orm.Set('Message', reverse='to_user')
            name = orm.Required(str)

        self.User = User

        class Message(self.db.Entity):
            text = orm.Required(str)
            from_user = orm.Required(User)
            to_user = orm.Required(User)
            time = orm.Required(int, size=64)

        self.Message = Message

    @orm.db_session
    def create_users(self):
        self.User(name='John')
        self.User(name='Bob')
        self.User(name='Susan')

    @orm.db_session
    def get_users(self):
        return [
            ObjectDict(id=u.id, name=u.name)
            for u in orm.select(u for u in self.User)
        ]

    @orm.db_session
    def get_user(self, pk=None, **kwargs):
        user = self.User[pk] if pk else self.User.get(**kwargs)
        return ObjectDict(id=user.id, name=user.name) if user else None

    @orm.db_session
    def save_message(self, text, from_user, to_user, time):
        self.Message(
            text=text,
            from_user=from_user,
            to_user=to_user,
            time=time
        )
