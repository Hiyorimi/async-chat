from pony import orm


class DAO:
    '''
    Data access object -- handles interactions with the database.
    '''
    def __init__(self, db_name='async_chat_db.sqlite'):
        self.db = orm.Database()
        self.db.bind('sqlite', db_name, create_db=True)
        self.define_entities()
        self.db.generate_mapping(create_tables=True)
        self.create_users()

    def define_entities(self):
        # Entity instances are stored in db.
        class User(self.db.Entity):
            from_messages = orm.Set('Message', reverse='from_user')
            to_messages = orm.Set('Message', reverse='to_user')
            name = orm.Required(str)

        self.User = User

        class Message(self.db.Entity):
            text = orm.Required(str)
            from_user = orm.Required(User)
            to_user = orm.Required(User)
            timestamp = orm.Required(int)

        self.Message = Message

    @orm.db_session
    def create_users(self):
        self.User(name='John')
        self.User(name='Bob')
