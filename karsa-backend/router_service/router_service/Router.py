import sys
import getopt

# from flask import Flask
# from flask_socketio import SocketIO
# flask_cors import CORS

import asyncio
import socketio
from aiohttp import web
import aiohttp_cors

from helpers import BaseServerNamespace


class RouterNamespace(BaseServerNamespace):
    pass


def parse_cmd_args():
    """Parse command line arguments
    Allowed command line arguments
    ------------------------------
    --url : string
        IP address (0.0.0.0)
    --port : int
        Server port (5010)
    """
    url = '0.0.0.0'
    port = 5010
    opts, _ = getopt.getopt(
                    sys.argv[1:],
                    'o:v',
                    ['url=', 'port=', ]
                    )
    for opt, arg in opts:
        if opt=='--url':
            url = arg
        if opt=='--port':
            try:
                port = int(arg)
            except:
                print('Invalid command line argument: %s=%s' %(opt, arg))
    return url, port


def run():
    url, port = parse_cmd_args()
    sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
    sio.register_namespace(RouterNamespace('/'))
    app = web.Application()
    sio.attach(app)
    cors = aiohttp_cors.setup(app)
    for resource in app.router._resources:
        if resource.raw_match("/socket.io/"):
            continue
        cors.add(resource, { '*': aiohttp_cors.ResourceOptions(allow_credentials=True, 
                                                               expose_headers="*", 
                                                               allow_headers="*") })
    web.run_app(app, host=url, port=port)


if __name__=='__main__':
    run()