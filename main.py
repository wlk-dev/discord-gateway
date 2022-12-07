import gateway, asyncio, os
from dotenv import load_dotenv

load_dotenv()

class Message:
    def __init__(self, message_json : dict) -> None:
        self.is_dm = not ( "guild_id" in message_json['d'] )
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

class Bot():
    def __init__(self, alias : str, token : str, intents : int) -> None:
        self.alias = alias
        self.token = token
        self.intents = intents
        gateway.register_bot(token, intents, alias)

    def run(self, url='wss://gateway.discord.gg'):
        asyncio.run( gateway.bot(url, self.alias) )

    @gateway.event()
    async def message_create(x):
        msg = Message(x)
        print(msg.unique_username, msg.content)
    
    @gateway.unhandled_event()
    async def other(x):
        print("Ignored Event : ", x['t'])
        print(x)

if __name__ == "__main__":
    url = 'wss://gateway.discord.gg'
    token = os.environ['bot_token']
    intents = 10 << 12

    bot = Bot('', token, intents)
    bot.run()


    # gateway.register_bot( token, intents)

    # @gateway.unhandled_event()
    # async def other(x):
    #     print("Ignored Event : ", x['t'])

    # @gateway.event()
    # async def message_create(x):
    #     print(x['d']['content'])

    # asyncio.run( gateway.bot(url) )