from random import random as _ran_random

import traceback
import websockets
import json
import asyncio

class BotRegisterError(Exception):
    ...

class BotError(Exception):
    ...

class opcode:
    """ containts opcode literals """
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

__bots__ = {}
__bot_callbacks__ = {}
__session_ids__ = {}

# Decorators tend to be evaluated first, so we need to catch the edge cases and ensure the handlers are saved before the bot is registered
# As we cant assign a handler to a bot that doesn't exist
# NOTE : this is a behavior that mainly occures when assigning function handlers that are a part of a class
def unhandled_event(bot_alias=''):
    """ All unhandled gateway event data will be sent to the decorated function. """
    def dummy(func):
        if bot_alias not in __bot_callbacks__:
            __bot_callbacks__[bot_alias] = { 'event_handlers' : {'dummy' : _dummy_callback}, 'func_handlers' : { 'unhandled_event_callback' : _dummy_callback } }
        else:
            __bot_callbacks__[bot_alias]['func_handlers']['unhandled_event_callback'] = func
        return func
    return dummy
    
def event(bot_alias=''):
    """
    `@gateway.event('my_bot_alias' : optional)` `async def message_create(x):`
    
    Received `MESSAGE_CREATE` event data will be routed to the decorated function, in the above case it would be `message_create()`.

    NOTE : function names MUST match event names, and are NOT case sensitive.
    """
    def dummy(func):
        if bot_alias not in __bot_callbacks__:
            __bot_callbacks__[bot_alias] = { 'event_handlers' : {func.__name__.lower() : func}, 'func_handlers' : { 'unhandled_event_callback' : _dummy_callback } }
        else:
            __bot_callbacks__[bot_alias]['event_handlers'][func.__name__.lower()] = func
        return func
    return dummy

def register_bot(token : str, intents : int, alias=''):
    """registers a bots info allowing for websocket connection, this also registers defined handler functions such as `gateway.message_create()` using the `@gateway.event()` decorator"""
    if alias in __bots__:
        raise BotRegisterError(f"A bot with alias, '{alias}' already exists.")
    
    __bots__[alias] = { "token" : token, "session_id" : '',  "session_state" : True, "session_code" : 0, "session_sequence" : 0,  "bot_intents" : intents, "hb_info" : (0,0), "tasks" : [], "ready_info" : {}, "func_handlers" : {'unhandled_event_callback' : _dummy_callback} ,"event_handlers" : {} }
    __bots__[alias].update(__bot_callbacks__[alias]) # Ensures that any pre-defined handlers are properly added to the bot

def get_bot(bot_alias : str) -> dict:
    """ returns a bot state dictionary with all known information on the requested bot """
    if (info := __bots__.get(bot_alias, False)):
        return info
    raise BotError(f"Could not find a session for bot '{bot_alias}'")

def _parse_heartbeat(raw_str : str) -> tuple[int, int]:
    """ takes raw hello data, returns -> tuple( heartbeat_interval_jitter, heartbeat_interval ) """
    interval = int( json.loads(raw_str)['d']['heartbeat_interval'] / 1000 )
    return int(interval*_ran_random()) , interval

def parse_json_str(raw_str : str) -> dict:
    """ parse a received json string, returns exit data if string was malformed or empty """
    try:
        return json.loads(raw_str)
    except json.JSONDecodeError as err:
        return { 'op':-2, 'd':False }
        ... # log err

#[ ---- bot getters / setters ---- ]
#[ ------------ START ------------ ]

def get_token(bot_alias='') -> str:
    return get_bot(bot_alias).get('token')

def get_intents(bot_alias='') -> int:
    return get_bot(bot_alias).get('intents')

def _set_session_id(session_id : str, bot_alias=''):
    get_bot(bot_alias)['session_id'] = session_id

def get_session_id(bot_alias='') -> str:
    return get_bot(bot_alias).get('session_id')

def _set_session_code(code : int, bot_alias=''):
    get_bot(bot_alias)['session_code'] = code

def _get_session_code(bot_alias='') -> int:
    return get_bot(bot_alias).get('session_code')

def _set_hb_info(info : tuple[int, int], bot_alias=''):
    """ set a bots hearbeat info, `info=(jitter_interval, interval)` """
    get_bot(bot_alias)['hb_info'] = info

def _get_hb_info(bot_alias='') -> tuple[int, int]:
    """ get a bots heartbeat info -> `(jitter_interval, interval)`  """
    return get_bot(bot_alias).get('hb_info')

def _set_session_state(state : bool, bot_alias=''):
    get_bot(bot_alias)['session_state'] = state

def _get_session_state(bot_alias='') -> bool:
    return get_bot(bot_alias).get('session_state')

def _set_ready_info(ready_info, bot_alias=''):
    get_bot(bot_alias)['ready_info'] = ready_info

def get_ready_info(bot_alias='') -> dict:
    return get_bot(bot_alias).get('ready_info')

def _set_sequence(seq : int, bot_alias=''):
    get_bot(bot_alias)['session_sequence'] = seq 

def _get_sequence(bot_alias='') -> int:
    return get_bot(bot_alias).get('session_sequence')

#[ ------------ END ------------ ]

# opcode payloads
def _get_identify_payload(bot_alias='') -> str:
    if get_intents(bot_alias) != 0:
        return json.dumps({ 'op' : 2,"d" : { "token" : get_token(bot_alias),"properties" : { "$os" : "windows", "$browser" : "chrome", "$device" : "pc" },'intents' : get_intents(bot_alias) } })
    return json.dumps({ 'op' : 2,"d" : { "token" : get_token(bot_alias),"properties" : { "$os" : "windows", "$browser" : "chrome", "$device" : "pc" } } })

def _get_resume_payload(bot_alias='') -> str:
    return json.dumps( { "op": 6,"d": { "token": get_token(bot_alias), "session_id": get_session_id(bot_alias), "seq":  _get_sequence(bot_alias) } } )



def bot_stop(bot_alias=''):
    """ exits session, then closes bot """
    _set_session_code(-1, bot_alias)
    _set_session_state(False, bot_alias)    

def bot_restart(bot_alias='', opcode=opcode.INVALID_SESSION):
    """ restart a bot with the given opcode """
    _set_session_code(opcode, bot_alias)
    _set_session_state(False, bot_alias)

async def _dummy_callback(*args, **kwargs):
    ...

async def _event_callback(callback, event : dict):
    try:
        await callback(event)
    except Exception as err:
        traceback.print_exc()

async def _cancel_tasks(bot_alias=''):
    for task in get_bot(bot_alias).get('tasks'):
        task.cancel()

async def _recv_handler(ws, event : dict, bot_alias : str) -> int:
    _set_sequence(event['s'] if 's' in event else 'null', bot_alias)
    opc = event['op']
    callback = None
    session_code = 0

    match opc:
        case opcode.DISPATCH:
            event_name = event['t'].lower()
            event_handlers = get_bot(bot_alias)['event_handlers']
            if event_name in event_handlers:
                callback = event_handlers[event_name]
            else:
                callback = get_bot(bot_alias)['func_handlers']['unhandled_event_callback']
        
        case opcode.HEARTBEAT:
            await ws.send( json.dumps( {"op": 1, "d": None} ) )
        
        case opcode.HEARTBEAT_ACK:
            ...
        
        case _:
            session_code = opc
    
    if callback is not None:
        await _event_callback(callback, event)
    
    return session_code

async def _recv_loop(ws, bot_alias : str):
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

async def _ping_loop(ws, bot_alias : str):
    jitter, hb_info = True, _get_hb_info(bot_alias)
    try:
        while _get_session_state(bot_alias):
            interval, jitter = ( hb_info[0] if jitter else hb_info[1] ), False # if its our first ping we want to use a jitter_interval not just jitter
            await asyncio.sleep(interval)
            await ws.send( json.dumps( {"op": 1, "d": None} ) ) 
            
    except asyncio.CancelledError:
        ...

async def _resume(ws, bot_alias : str):
    await ws.send( _get_resume_payload(bot_alias) )
    resume_payload = parse_json_str( await ws.recv() )
    return resume_payload

async def _identify(ws, bot_alias : str) -> tuple[bool, dict]:
    await ws.send( _get_identify_payload(bot_alias) )
    ready_payload = parse_json_str( await ws.recv() )
    _set_ready_info(ready_payload, bot_alias)
    return ready_payload

async def _init_session(ws, bot_alias : str) -> int:
    _set_hb_info( _parse_heartbeat(await ws.recv()) , bot_alias)

    session_code = _get_session_code(bot_alias)

    if session_code == opcode.RECONNECT:
        resp = await _resume(ws, bot_alias)
    else:
        resp = await _identify(ws, bot_alias)
        _set_session_id(resp['d']['session_id'], bot_alias)

    _set_session_code(resp['op'], bot_alias)
    return resp['op']
    
async def init_connection(bot_alias : str, gateway_url : str):
    async with websockets.connect( gateway_url, max_size=10_000_000 ) as ws:
        session_code = await _init_session(ws, bot_alias)
        
        if session_code != opcode.INVALID_SESSION:
            ... # log session info
            print( get_session_id(bot_alias), _get_hb_info(bot_alias) )

            ping = asyncio.create_task( _ping_loop(ws, bot_alias) )
            recv = asyncio.create_task( _recv_loop(ws, bot_alias) )

            get_bot(bot_alias)['tasks'] = (ping, recv)
            await ping, recv
        
        await ws.close()

async def bot(url : str, alias=''):
    """ entry point for a registered bot, should be run in main event loop   """
    while True:
        try:
            await init_connection(alias, url)
        except websockets.ConnectionClosed as err:
            ... # impl logging callback
            traceback.print_exc()
        
        session_code = _get_session_code(alias) # session code is set internally on bot restart/stop 
        _set_session_state(True, alias) # session must be active or event loops will not start 

        if session_code == opcode.INVALID_SESSION:
            await asyncio.sleep(7)
        
        elif session_code == opcode.RECONNECT:
            pass
        
        else:
            break

if __name__ == "__main__":
    ...