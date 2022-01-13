import inspect

from socketio import AsyncNamespace

from .util import get_client_notification_context



class BaseServerNamespace(AsyncNamespace):
    """ socketio server base namespace class """

    def log(self, *arg, **kwarg):
        print(f"[{self.namespace}.{inspect.stack()[1].function}]", *arg, **kwarg)

    async def on_connect(self, sid, environ):
        self.log(sid, "connected to namespace", self.namespace)

    async def on_disconnect(self, sid):
        self.log(sid, "disconnected from namespace", self.namespace)
        # clear the app caches, if any, in all app services
        # TODO:
        # let affected rooms know the client is gone
        for r in self.rooms(sid):
            await self.emit('room_mate_gone', {}, room=r)


    # async def on_subscribe(self, sid, data):
    #     """
    #     Initialize client subscriptions. Subscriptions contain notif names
    #     the client subscribes for and a room to subscribe into.
    #     data: dict(app_name=client_name, endpoints, room)
    #     """
    #     app_name = data['app_name']
    #     endpoints = data['endpoints']
    #     room = data.get('room')
    #     if room:
    #         self.log(f"{app_name}:{sid} joins room {room}")
    #         self.enter_room(sid, room)
    #     else:
    #         self.log(f"{app_name}:{sid} joins rooms {endpoints}")
    #         for e in endpoints:
    #             self.enter_room(sid, e)
    #     self.log(f"{app_name}:{sid} stays in rooms: {self.rooms(sid)}")
    #     await self.emit('service_state', {})

    # async def on_unsubscribe(self, sid, data):
    #     app_name = data['app_name']
    #     endpoints = data['endpoints']
    #     room = data.get('room')
    #     if room:
    #         self.log(f"{app_name}:{sid} leaves room {room}")
    #         self.leave_room(sid, room)
    #         await self.emit('service_state', {}, room=room)
    #     else:
    #         self.log(f"{app_name}:{sid} leaves rooms {endpoints}")
    #         for e in endpoints:
    #             self.leave_room(sid, e)
    #     self.log(f"{app_name}:{sid} stays in rooms: {self.rooms(sid)}")



    async def on_declare_endpoints(self, sid, data):
        """
        Declare API from a client service by creating a room for each API function.
        API requests are sent thru Router via client_notifications:
        Client->Router->Service
        The API room is used to send this request to only those services,
        which declare corresponding API.
        data: list(app_name=client_name, endpoints)
        """
        app_name = data['app_name']
        endpoints = data['endpoints']
        for e in endpoints:
            self.enter_room(sid, e)
        # self.log(f"{app_name}:{sid} declares endpoints {endpoints}")
        self.log(f"{app_name} stays in rooms: {self.rooms(sid)}")
        await self.emit('service_state', {})

    async def on_enter_room(self, sid, data):
        app_name = data['app_name']
        room = data['room']
        self.enter_room(sid, room)
        self.log(f"{app_name} : {room}")

    def on_leave_room(self, sid, data):
        app_name = data['app_name']
        room = data['room']
        self.leave_room(sid, room)
        self.log(f"{app_name} : {room}")

    async def on_client_notification(self, sid, data):
        """
        client_notifications on corresponding API endpoints are forwarded by Router from requesters
        to providers via corresponding endpoints, where name = endpoint is a property name.
        data: dict(name=endpoint_name, value=endpoint_value, ...)
              other named args are free form, e.g. 
              room, cookies, no_logging, no_data_logging...
        """
        no_logging = data.get('no_logging', False)
        no_data_logging = data.get('no_data_logging', True)
        endpoint = data['name']
        room = data.get('room')
        namespace = data.get('namespace', self.namespace)
        cb = data.pop('callback', None)
        cb_ctx = data.pop('callback_context', None)

        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{endpoint}: ...")
        else:
            self.log(data)

        if 'cookies' not in data:
            data['cookies'] = dict(src_sid=[])
        elif 'src_sid' not in data['cookies']:
            data['cookies']['src_sid']=[]
        cookies = data['cookies']
        src_sids = cookies['src_sid']
        # sids are added to the cookies only by this procedure
        src_sids.append(sid)

        target_room = room if room else endpoint

        async def srv_callback(*arg, **kwarg):
            await self.emit('client_notification_callback',
                            dict(endpoint=endpoint,
                                 cb_name=cb, cb_ctx=cb_ctx,
                                 arg=arg, kwarg=kwarg,
                                 **{**get_client_notification_context(data), 'no_logging': True}),
                            room=sid,
                            namespace=self.namespace
                            )
        sent_to = len(src_sids) * '>'
        self.log(f"{endpoint} {sent_to} {namespace}:{target_room}")
        await self.emit(endpoint, data, room=target_room, namespace=namespace, callback=cb and srv_callback)



