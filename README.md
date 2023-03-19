# Discord Gateway
This Python module provides an advanced implementation of the Discord Gateway, enabling the creation and management of Discord bot connections. The module includes functions for connecting, restarting, stopping, and sending messages to the Discord Gateway, as well as event handling, parsing, and managing bot sessions. It is designed for performance and flexibility, with support for multiple bots and customizable event parsers.

## Features
- Register and manage multiple bots with aliases for easy identification
- Event handling through decorators, allowing for modular and organized code
- Customizable event parsers to support different data formats and requirements
- Asynchronous implementation using asyncio and websockets for improved performance and responsiveness
- Comprehensive set of utility functions for managing bot state and interactions with the Discord Gateway

## Usage
### Bot Registration
To register a bot, use the `register_bot()` function with its token, intents, and an optional alias:

```python
register_bot(token, intents, alias)
```

## Event Handling
Define your event handlers using the `@event()` decorator. This decorator takes two optional arguments: `bot_alias` and `event_parser`. The `bot_alias` is the alias of the bot the event handler is for, while `event_parser` is a custom parser function for processing event data.

```python
@event(bot_alias='', event_parser=_dummy_parser)
async def message_create(x):
    ...
```

## Connection Initialization
To initialize and run the bot's connection, use the `bot()` function with the gateway URL and the bot alias. This function should be called within an asyncio event loop:

```python
async def main():
    await bot(url, alias)

asyncio.run(main())
```

## Functions
The module provides various functions for managing bot connections, event handling, and bot state management. For a detailed overview of available functions, refer to the code comments and docstrings.

Some key functions include:

- `register_bot()`: Registers a bot with the given token, intents, and alias
- `get_bot()`: Retrieves a bot's state dictionary with all known information
- `bot_stop()`: Exits the bot's session and closes the connection
- `bot_restart()`: Restarts the bot's connection with the given opcode
- `bot_send()`: Sends a payload to the Discord Gateway
Please note that some functions are meant to be used internally and are not intended for direct use. These functions are prefixed with an underscore (_).

## Dependencies
- Python 3.7+
- [websockets](https://pypi.org/project/websockets/)

## License
This code is provided under the [MIT License](https://opensource.org/licenses/MIT).

## Disclaimer
This implementation is not officially supported or endorsed by Discord. Use at your own risk and ensure compliance with the [Discord Developer Terms of Service](https://discord.com/developers/docs/legal).
