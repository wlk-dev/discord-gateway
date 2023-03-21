from random import random as _ran_random
from typing import Callable

import traceback
import websockets
import json
import asyncio


class BotRegisterError(Exception):
    """Raised when there is an error during bot registration."""
    ...

class BotError(Exception):
    """Raised when there is a general bot-related error."""
    ...

class opcode:
    """Contains opcode literals for Discord gateway events."""
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESCENCE_UPDATE = 3
    VOICE_STATE_UPDATE = 4
    RESUME = 6
    RECONNECT = 7
    REQUEST_GUILD_MEMBERS = 8
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11


async def _default_parser(event: dict[str, any]) -> dict[str, any]:
    """
    Default event parser. Will always be overwritten if something else is specified.

    Args:
        event (dict[str, any]): The event data.

    Returns:
        dict[str, any]: The event data.
    """
    return event

async def _dummy_callback(*args, **kwargs) -> None:
    """
    Dummy callback function that does nothing.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    pass

__bots__ = {}
__bot_callbacks__ = {}
__session_ids__ = {}

# Decorators tend to be evaluated first, so we need to catch the edge cases and ensure the handlers are saved before the bot is registered
# As we cant assign a handler to a bot that doesn't exist
# NOTE : this is a behavior that mainly occures when assigning function handlers that are a part of a class
def unhandled_event(bot_alias: str = '', event_parser: Callable = _default_parser, raw: bool = False) -> Callable:
    """
    Decorator for unhandled event handlers. All unhandled gateway event data will be sent to the decorated function.

    Args:
        bot_alias (str, optional): The bot alias. Defaults to ''.
        event_parser (Callable, optional): The event parser function. Defaults to _default_parser.
        raw (bool, optional): If set to True, this parameter disables the current parser and uses the raw event data for the decorated function. If set to False (default), the current parser is used.

    Returns:
        Callable: The decorator function.
    """
    event_parser = _default_parser if raw else event_parser

    def dummy(func: Callable) -> Callable:
        if bot_alias not in __bot_callbacks__:
            __bot_callbacks__[bot_alias] = {
                'event_handlers': {'dummy': (_dummy_callback, event_parser)},
                'func_handlers': {'unhandled_event_callbacks': (_dummy_callback, event_parser)}
            }
        else:
            __bot_callbacks__[bot_alias]['func_handlers']['unhandled_event_callbacks'] = (func, event_parser)
        return func

    return dummy

def event(bot_alias: str = '', event_parser: Callable = _default_parser, raw: bool = False) -> Callable:
    """
    Decorator for gateway event handlers.

    This decorator routes the received event data to the decorated function, based on the event name.
    If an `event_parser` is specified, the event data will be parsed before being sent to the decorated function.
    
    Usage:
    ```
    @event('my_bot_alias', event_parser=_my_parser)
    async def message_create(x):
    ```

    NOTE: Function names must match event names and are not case sensitive.

    Args:
        bot_alias (str, optional): Alias of the bot. Defaults to ''.
        event_parser (Callable, optional): Function to parse the event data. Defaults to _default_parser.
        raw (bool, optional): Whether to use the raw event data. Defaults to False.

    Returns:
        Callable: The decorator function.
    """

    event_parser = _default_parser if raw else event_parser

    def dummy(func: Callable) -> Callable:
        if bot_alias not in __bot_callbacks__:
            __bot_callbacks__[bot_alias] = {
                'event_handlers': {func.__name__.lower(): (func, event_parser)},
                'func_handlers': {'unhandled_event_callbacks': (_dummy_callback, event_parser)}
            }
        else:
            __bot_callbacks__[bot_alias]['event_handlers'][func.__name__.lower()] = (func, event_parser)
        return func

    return dummy

def register_bot(token: str, intents: int, alias: str = '', event_parser: Callable = None, obj_instance: any = None) -> None:
    """
    Registers a bot's info allowing for websocket connection.
    This also registers defined handler functions such as `gateway.message_create()` using the `@event()` decorator.

    Args:
        token (str): The bot token.
        intents (int): The bot intents.
        alias (str, optional): The bot alias. Defaults to ''.
        event_parser (Callable, optional): The event parser function. Defaults to None.
        obj_instance (any, optional): An instance of the class containing methods decorated with the `@event()` decorator, if any. Defaults to None.

    Raises:
        BotRegisterError: If a bot with the given alias already exists.
    """

    if alias in __bots__:
        raise BotRegisterError(f"A bot with alias, '{alias}' already exists.")

    __bots__[alias] = {
        "token": token,
        "obj_instance": obj_instance,
        "session_id": '',
        "session_state": True,
        "session_code": 0,
        "session_sequence": 0,
        "bot_intents": intents,
        "hb_info": (0, 0),
        "tasks": [],
        "queue": asyncio.Queue(),
        "ready_info": {},
        "func_handlers": {'unhandled_event_callbacks': (_dummy_callback, _default_parser)},
        "event_handlers": {},
        "event_parser": event_parser
    }
    __bots__[alias].update(__bot_callbacks__[alias])  # Ensures that any pre-defined handlers are properly added to the bot

def get_bot(bot_alias: str) -> dict:
    """
    Returns a bot state dictionary with all known information on the requested bot.

    Args:
        bot_alias (str): The bot alias.

    Returns:
        dict: The bot state dictionary.

    Raises:
        BotError: If the requested bot alias cannot be found.
    """
    if (info := __bots__.get(bot_alias, False)):
        return info
    raise BotError(f"Could not find a session for bot '{bot_alias}'")

def _parse_heartbeat(raw_str: str) -> tuple[int, int]:
    """
    Takes raw hello data and returns a tuple with heartbeat_interval_jitter and heartbeat_interval.

    Args:
        raw_str (str): The raw hello data in string format.

    Returns:
        tuple[int, int]: A tuple containing the heartbeat_interval_jitter and heartbeat_interval.
    """
    interval = int(json.loads(raw_str)['d']['heartbeat_interval'] / 1000)
    return int(interval * _ran_random()), interval


def parse_json_str(raw_str: str) -> dict:
    """
    Parses a received JSON string and returns exit data if the string was malformed or empty.

    Args:
        raw_str (str): The raw JSON string.

    Returns:
        dict: Parsed JSON data or exit data if the string is malformed or empty.
    """
    try:
        return json.loads(raw_str)
    except json.JSONDecodeError as err:
        return {'op': -2, 'd': False}
        # TODO: log err


# [ ---- bot getters / setters ---- ]
# [ ------------ START ------------ ]

def get_token(bot_alias='') -> str:
    """Get the bot token for the specified bot alias."""
    return get_bot(bot_alias).get('token')

def get_intents(bot_alias='') -> int:
    """Get the bot intents for the specified bot alias."""
    return get_bot(bot_alias).get('intents')

def _set_session_id(session_id: str, bot_alias=''):
    """Set the session ID for the specified bot alias."""
    get_bot(bot_alias)['session_id'] = session_id

def get_session_id(bot_alias='') -> str:
    """Get the session ID for the specified bot alias."""
    return get_bot(bot_alias).get('session_id')

def _set_session_code(code: int, bot_alias=''):
    """Set the session code for the specified bot alias."""
    get_bot(bot_alias)['session_code'] = code

def _get_session_code(bot_alias='') -> int:
    """Get the session code for the specified bot alias."""
    return get_bot(bot_alias).get('session_code')

def _set_hb_info(info: tuple[int, int], bot_alias=''):
    """
    Set the bot's heartbeat info for the specified bot alias.

    Args:
        info (tuple[int, int]): A tuple containing the jitter_interval and interval.
        bot_alias (str, optional): The bot alias. Defaults to ''.
    """
    get_bot(bot_alias)['hb_info'] = info

def _get_hb_info(bot_alias='') -> tuple[int, int]:
    """
    Get the bot's heartbeat info for the specified bot alias.

    Returns:
        tuple[int, int]: A tuple containing the jitter_interval and interval.
    """
    return get_bot(bot_alias).get('hb_info')

def _set_session_state(state: bool, bot_alias=''):
    """Set the session state for the specified bot alias."""
    get_bot(bot_alias)['session_state'] = state

def _get_session_state(bot_alias='') -> bool:
    """Get the session state for the specified bot alias."""
    return get_bot(bot_alias).get('session_state')

def _set_ready_info(ready_info, bot_alias=''):
    """Set the ready info for the specified bot alias."""
    get_bot(bot_alias)['ready_info'] = ready_info

def get_ready_info(bot_alias='') -> dict:
    """Get the ready info for the specified bot alias."""
    return get_bot(bot_alias).get('ready_info')

def _set_sequence(seq: int, bot_alias=''):
    """Set the session sequence for the specified bot alias."""
    get_bot(bot_alias)['session_sequence'] = seq

def _get_sequence(bot_alias='') -> int:
    """Get the session sequence for the specified bot alias."""
    return get_bot(bot_alias).get('session_sequence')

# [ ------------ END ------------ ]


# opcode payloads
def _get_identify_payload(bot_alias='') -> str:
    """
    Get the identify payload for the specified bot alias.

    Returns:
        str: A JSON-formatted identify payload for the bot.
    """
    if get_intents(bot_alias) != 0:
        return json.dumps({'op': 2, "d": {"token": get_token(bot_alias), "properties": {"$os": "windows", "$browser": "chrome", "$device": "pc"}, 'intents': get_intents(bot_alias)}})
    return json.dumps({'op': 2, "d": {"token": get_token(bot_alias), "properties": {"$os": "windows", "$browser": "chrome", "$device": "pc"}}})

def _get_resume_payload(bot_alias='') -> str:
    """
    Get the resume payload for the specified bot alias.

    Returns:
        str: A JSON-formatted resume payload for the bot.
    """
    return json.dumps({"op": 6, "d": {"token": get_token(bot_alias), "session_id": get_session_id(bot_alias), "seq": _get_sequence(bot_alias)}})

def bot_stop(bot_alias=''):
    """
    Exit the session and close the bot for the given bot alias.

    Args:
        bot_alias (str): The alias of the bot to stop. Defaults to an empty string.
    """
    _set_session_code(-1, bot_alias)
    _set_session_state(False, bot_alias)    

def bot_restart(bot_alias='', opcode=opcode.INVALID_SESSION):
    """
    Restart a bot with the given opcode.

    Args:
        bot_alias (str): The alias of the bot to restart. Defaults to an empty string.
        opcode (int): The opcode to use when restarting the bot. Defaults to opcode.INVALID_SESSION.
    """
    _set_session_code(opcode, bot_alias)
    _set_session_state(False, bot_alias)

async def bot_send(payload: dict, bot_alias=''):
    """
    Add a payload to the send queue of the bot with the given bot alias.

    Args:
        payload (dict): The payload to send.
        bot_alias (str): The alias of the bot for which queue the payload should be added to. Defaults to an empty string.
    """
    get_bot(bot_alias)['queue'].put(payload)

async def _event_callback(callbacks: tuple, event: dict, bot_alias=''):
    """
    Call the appropriate event callback with the parsed event data.

    Args:
        callbacks (tuple): A tuple containing the callback function and event parser.
        event (dict): The event data to be processed.
        bot_alias (str): The alias of the bot associated with the event. Defaults to an empty string.
    """
    instance = get_bot(bot_alias)['obj_instance']
    callback, parser = callbacks
    try:
        event_data = await parser(event)
        data = (instance, event_data) if instance is not None else (event_data,)
        await callback(*data)
    except Exception as err:
        traceback.print_exc()

async def _cancel_tasks(bot_alias=''):
    """
    Cancel all tasks associated with the given bot alias.

    Args:
        bot_alias (str): The alias of the bot whose tasks should be canceled. Defaults to an empty string.
    """
    for task in get_bot(bot_alias).get('tasks'):
        task.cancel()

async def _recv_handler(ws, event: dict, bot_alias: str) -> int:
    """
    Handle incoming events from the WebSocket connection and call appropriate callbacks.

    Args:
        ws: The WebSocket connection to send and receive messages.
        event (dict): The event data received from the WebSocket.
        bot_alias (str): The alias of the bot associated with the event.

    Returns:
        int: The opcode of the received event.
    """
    _set_sequence(event['s'] if 's' in event else 'null', bot_alias)
    opc = event['op']
    callbacks = None
    session_code = 0

    match opc:
        case opcode.DISPATCH:
            event_name = event['t'].lower()
            event_handlers = get_bot(bot_alias)['event_handlers']
            if event_name in event_handlers:
                callbacks = event_handlers[event_name]
            else:
                callbacks = get_bot(bot_alias)['func_handlers']['unhandled_event_callbacks']

        case opcode.HEARTBEAT:
            await ws.send(json.dumps({"op": 1, "d": None}))

        case opcode.HEARTBEAT_ACK:
            ...

        case _:
            session_code = opc

    if callbacks is not None:
        # If a parser has been registered with the bot, use the registered parser only if one was not specified in the @gateway.event() decorator.
        # -- eg. if the parser is specified here --> @gateway.event(event_parser=SpecificParser) <--- then use it, or else use what the bot was registered with
        parser = get_bot(bot_alias)['event_parser']
        callbacks = (callbacks[0], parser) if (parser is not None and callbacks[1] is _default_parser) else callbacks
        await _event_callback(callbacks, event, bot_alias)

    return session_code


async def _recv_loop(ws, bot_alias: str):
    """
    Continuously receive events from the WebSocket connection and process them.

    Args:
        ws: The WebSocket connection to receive messages.
        bot_alias (str): The alias of the bot associated with the event.

    Raises:
        asyncio.CancelledError: Raised if the loop is cancelled.
    """
    try:
        async for event in ws:
            session_code = await _recv_handler(ws, parse_json_str(event), bot_alias)
            if session_code != opcode.DISPATCH or not _get_session_state(bot_alias):
                bot_restart(bot_alias, session_code)
                await ws.close()

    except asyncio.CancelledError:
        pass

    finally:
        await _cancel_tasks(bot_alias)

async def _send_loop(ws, bot_alias: str):
    """
    Continuously send queued messages through the WebSocket connection.

    Args:
        ws: The WebSocket connection to send messages.
        bot_alias (str): The alias of the bot associated with the event.

    Raises:
        json.JSONDecodeError: Raised if there is an issue with JSON encoding.
        asyncio.CancelledError: Raised if the loop is cancelled.
    """
    queue = get_bot(bot_alias)['queue']
    try:
        while _get_session_state(bot_alias):
            msg = await queue.get()
            await ws.send(json.dumps(msg))

    except json.JSONDecodeError:
        traceback.print_exc()

    except asyncio.CancelledError:
        pass

    finally:
        ...
        # await _cancel_tasks(bot_alias)
        # look into Queue clearing if need be


async def _ping_loop(ws, bot_alias: str):
    """
    Continuously send heartbeat messages through the WebSocket connection.

    Args:
        ws: The WebSocket connection to send heartbeat messages.
        bot_alias (str): The alias of the bot associated with the event.

    Raises:
        asyncio.CancelledError: Raised if the loop is cancelled.
    """
    jitter, hb_info = True, _get_hb_info(bot_alias)
    try:
        while _get_session_state(bot_alias):
            # If it's our first ping, use a jitter_interval, not just jitter
            interval, jitter = (hb_info[0] if jitter else hb_info[1]), False
            await asyncio.sleep(interval)
            await ws.send(json.dumps({"op": 1, "d": None}))

    except asyncio.CancelledError:
        ...


async def _resume(ws, bot_alias: str):
    """
    Resume the bot's session by sending a resume payload through the WebSocket connection.

    Args:
        ws: The WebSocket connection to send the resume payload.
        bot_alias (str): The alias of the bot associated with the event.

    Returns:
        resume_payload (dict): The parsed JSON response from the WebSocket after resuming.
    """
    await ws.send(_get_resume_payload(bot_alias))
    resume_payload = parse_json_str(await ws.recv())
    return resume_payload

async def _identify(ws, bot_alias: str) -> tuple[bool, dict]:
    """
    Identify the bot's session by sending an identify payload through the WebSocket connection.

    Args:
        ws: The WebSocket connection to send the identify payload.
        bot_alias (str): The alias of the bot associated with the event.

    Returns:
        tuple[bool, dict]: A tuple containing a boolean value indicating the success of identification
                           and a dictionary containing the parsed JSON response from the WebSocket.
    """
    await ws.send(_get_identify_payload(bot_alias))
    ready_payload = parse_json_str(await ws.recv())
    _set_ready_info(ready_payload, bot_alias)
    return ready_payload


async def _init_session(ws, bot_alias: str) -> int:
    """
    Initialize the bot's session by parsing the heartbeat and setting the session code.

    Args:
        ws: The WebSocket connection to initialize the session.
        bot_alias (str): The alias of the bot associated with the event.

    Returns:
        int: The operation code (opcode) after initializing the session.
    """
    _set_hb_info(_parse_heartbeat(await ws.recv()), bot_alias)

    session_code = _get_session_code(bot_alias)

    if session_code == opcode.RECONNECT:
        resp = await _resume(ws, bot_alias)
    else:
        resp = await _identify(ws, bot_alias)
        _set_session_id(resp['d']['session_id'], bot_alias)

    _set_session_code(resp['op'], bot_alias)
    return resp['op']

async def init_connection(bot_alias: str, gateway_url: str):
    """
    Initialize the connection to the Discord Gateway for the bot.

    Args:
        bot_alias (str): The alias of the bot associated with the event.
        gateway_url (str): The URL of the Discord Gateway to connect to.

    Returns:
        None
    """
    async with websockets.connect(gateway_url, max_size=10_000_000) as ws:
        session_code = await _init_session(ws, bot_alias)

        if session_code != opcode.INVALID_SESSION:
            # Log session info
            print(get_session_id(bot_alias), _get_hb_info(bot_alias))

            ping = asyncio.create_task(_ping_loop(ws, bot_alias))
            recv = asyncio.create_task(_recv_loop(ws, bot_alias))
            send = asyncio.create_task(_send_loop(ws, bot_alias))

            get_bot(bot_alias)['tasks'] = (ping, recv, send)
            await ping, recv, send

        await ws.close()


async def bot(url: str, alias: str = ''):
    """
    Entry point for a registered bot. Should be run in the main event loop.

    Args:
        url (str): The Discord Gateway URL.
        alias (str, optional): The alias of the bot associated with the event. Defaults to an empty string.

    Returns:
        None
    """
    while True:
        try:
            await init_connection(alias, url)
        except websockets.ConnectionClosed as err:
            # Implement logging callback
            traceback.print_exc()

        session_code = _get_session_code(alias)  # Session code is set internally on bot restart/stop
        _set_session_state(True, alias)  # Session must be active or event loops will not start

        if session_code == opcode.INVALID_SESSION:
            await asyncio.sleep(7)

        elif session_code == opcode.RECONNECT:
            pass

        else:
            break


if __name__ == "__main__":
    ...