import os

from pony import orm
from tornado.util import ObjectDict


DB_NAME = 'async_chat.sqlite'


try:
    os.remove(DB_NAME)
except FileNotFoundError:
    pass


DB = orm.Database('sqlite', DB_NAME, create_db=True)


class User(DB.Entity):
    from_messages = orm.Set('Message', reverse='from_user')
    to_messages = orm.Set('Message', reverse='to_user')
    name = orm.Required(str)


class Message(DB.Entity):
    text = orm.Required(str)
    from_user = orm.Required(User)
    to_user = orm.Required(User)
    time = orm.Required(int, size=64)


DB.generate_mapping(create_tables=True)


# All data retrieving methods return dicts because of the way
# Pony orm works (see db_session decorator explanation).
class DataAccessObject:
    '''
    Data access object -- handles interactions with the database.
    '''
    def __init__(self, db, *entities):
        self.db = DB
        for entity in entities:
            setattr(self, entity.__name__, entity)
        self.create_users()

    def define_entities(self):

        self.User = User

        self.Message = Message

    @orm.db_session
    def create_users(self):
        self.User(name='John')
        self.User(name='Bob')
        self.User(name='Susan')

    @orm.db_session
    def get_users(self):
        return [
            ObjectDict(
                id=u.id,
                name=u.name,
            ) for u in orm.select(u for u in self.User)
        ]

    @orm.db_session
    def get_user(self, pk=None, **kwargs):
        user = self.User[pk] if pk else self.User.get(**kwargs)
        return ObjectDict(
            id=user.id,
            name=user.name,
        ) if user else None

    @orm.db_session
    def save_message(self, text, from_user, to_user, time):
        self.Message(
            text=text,
            from_user=from_user,
            to_user=to_user,
            time=time
        )
