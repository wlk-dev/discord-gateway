import gateway, asyncio, os
from dotenv import load_dotenv

class Event:
    def __init__(self, event_data : dict) -> None:
        self.NAME = event_data['t'] # would "TYPE" fit better?
        self.raw = event_data
        self.guild_related = ( "guild_id" in event_data['d'] )

    @classmethod
    async def parse_event(cls, event : dict):
        return cls(event)

class Message(Event):
    def __init__(self, message_json : dict) -> None:
        super().__init__(message_json)
        self.is_dm = not self.guild_related
        self.raw = message_json

        self.__parse_message__( message_json['d'] )
        self.__parse_author__( message_json['d']['author'] )

    def __parse_message__(self, msg : dict):
        self.guild_id = msg.get('guild_id', '')
        self.channel_id = msg.get('channel_id', '')
        self.message_id = msg.get('id', '')
        self.content = msg.get('content', '')

    def __parse_author__(self, msg : dict):
        self.username = msg.get('username', '')
        self.discriminator = msg.get('discriminator', '')
        self.user_id = msg.get('id', '')
        self.unique_username = f"{self.username}#{self.discriminator}"

class Presence(Event):
    def __init__(self, presence_json) -> None:
        super().__init__(presence_json)

        self.__parse_presence__(presence_json['d'])

    def __parse_presence__(self, presence: dict):
        self.target_user = presence.get('user')['id']
        self.target_username = presence['user'].get('username')
        self.target_discriminator = presence['user'].get('discriminator')
        self.activities = presence.get('activities', '')
    
    @classmethod
    async def parse_event(cls, event):
        return cls(event)

class Bot():
    def __init__(self, alias : str, token : str, intents : int, event_parser=None) -> None:
        self.alias = alias
        self.token = token
        self.intents = intents
        self.last_message = None
        gateway.register_bot(token, intents, alias, event_parser, obj_instance=self)

    def run(self, url='wss://gateway.discord.gg'):
        asyncio.run( gateway.bot(url, self.alias) )

    @gateway.event(event_parser=Message.parse_event)
    async def message_create(self, msg: Message):
        print(msg.unique_username, msg.content)
        self.last_message = msg
    
    @gateway.event()
    async def presence_update(self, presence: Presence):
        if not presence.guild_related:
            print(presence.NAME, presence.target_username, presence.activities)
    
    @gateway.unhandled_event()
    async def other(self, x):
        print(x)

async def parser(event):
    event_name = event['t'].lower()
    if event_name == "message_create":
        return await Message.parse_event(event)
    elif event_name == "presence_update":
        return await Presence.parse_event(event)

    event = Event(event)    
    return f"Ignored Event : {event.NAME}"

if __name__ == "__main__":
    # load_dotenv()

    url = 'wss://gateway.discord.gg'
    # token = os.environ['bot_token']
    token = "NzgyNzYyNTQ2Mzc3NTIzMjEx.Gu1wH_.4cIiISwRA6qsbG1eHoLkQbOzIdXHmezorD4M_g"
    intents = 10 << 12
    

    bot = Bot('', token, intents, event_parser=parser)
    bot.run()


    # gateway.register_bot(token, intents, event_parser=parser)

    # @gateway.unhandled_event(raw=True)
    # async def other(x):
    #     print("Ignored Event : ", x['t'])

    # @gateway.event()
    # async def message_create(x):
    #     print(x.unique_username, x.content)

    # asyncio.run( gateway.bot(url) )