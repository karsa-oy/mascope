import inspect
from copy import deepcopy
import random
from socketio import AsyncClientNamespace, AsyncNamespace

NO_LOGGING_DEFAULT = False
NO_DATA_LOGGING_DEFAULT = True

class BaseClientNamespace(AsyncClientNamespace):
    """ python-socket.io client namespace for connecting to Router """
    # rooms - list of notifications the client wants to receive from socket server
    rooms = []
    # service_state - state vars to report to (re)starting subscribers
    service_state = {}
    # app_name is used to detect twin apps
    app_name = __file__
    # type is used to diff service app from client app (python apps are normally services)
    app_type = 'service'

    def log(self, *arg, **kwarg):
        if not NO_LOGGING_DEFAULT:
            print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    async def join_rooms(self):
        data = dict(
            app_name = self.app_name,
            app_type = self.app_type,
            subscriptions = self.rooms,
        )
        await self.emit('subscribe', data)

    async def on_connect(self):
        self.app_name = self.__class__.__name__
        self.log(f"connected to namespace {self.namespace}")
        await self.join_rooms()

    def on_disconnect(self):
        self.log(f"disconnected from namespace {self.namespace}")

    async def on_service_state(self, data):
        no_logging = data.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = data.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        cookies = data['cookies']
        for k, v in self.service_state.items():
            if no_logging:
                pass
            elif no_data_logging:
                self.log(f"{k}: ...")
            else:
                self.log(f"{k}: {v}")
            await self.emit('client_notification', {'name': k, 'value': v, 'cookies': cookies})

    async def emit_client_notification(self, name, value, **kwarg):
        no_logging = kwarg.get('no_logging', NO_LOGGING_DEFAULT)
        no_data_logging = kwarg.get('no_data_logging', NO_DATA_LOGGING_DEFAULT)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{name}: ...")
        else:
            self.log(f"{name}: {value}")
        await self.emit('client_notification', {'name': name, 'value': value, **kwarg})
        if name in self.service_state:
            self.service_state[name] = value


class BaseServerNamespace(AsyncNamespace):
    """ socketio server base namespace class """
    subscription_sids = dict()
    sid_to_app = dict()
    app_name_to_sids = dict()   # for tracing service/app twins

    def log(self, *arg, **kwarg):
        print(f"[{self.__class__.__name__}.{inspect.stack()[1].function}]", *arg, **kwarg)

    def add_subscription(self, sid, room):
        if room not in self.subscription_sids:
            self.subscription_sids[room] = []
        if sid not in self.subscription_sids[room]:
            self.subscription_sids[room].append(sid)
        self.enter_room(sid, f'{room}_{sid}')

    def remove_subscription(self, sid, room):
        self.leave_room(sid, f'{room}_{sid}')
        self.subscription_sids[room].remove(sid)
    
    def on_connect(self, sid, environ):
        self.log("connected to namespace", self.namespace)

    def on_disconnect(self, sid):
        if sid not in self.sid_to_app:
            # don't unsubscribe anonimous clients (UI:renderer?)
            return
        app_name = self.sid_to_app[sid]['name']
        app_type = self.sid_to_app[sid].get('type', 'client')
        self.log(app_type, app_name, "disconnected from namespace", self.namespace)
        for room in self.subscription_sids:
            try:
                self.remove_subscription(sid, room)
            except:
                pass
        del self.sid_to_app[sid]
        self.app_name_to_sids[app_name].remove(sid)
        if not self.app_name_to_sids[app_name]:
            del self.app_name_to_sids[app_name]

    def on_subscribe(self, sid, data):
        """
        Initialize client subscriptions. 
        Subscriptions contain prop names the client subscribes for.
        data: dict(app_name=client_name, [app_name=client_type,] subscriptions=subscription_list)
        """
        app_name = data['app_name']
        app_type = data.get('app_type', 'client')
        self.log(f"{app_type} {app_name}:{sid} joined rooms {data['subscriptions']}")
        self.sid_to_app[sid] = dict(name=app_name, type=app_type)
        if app_name not in self.app_name_to_sids:
            self.app_name_to_sids[app_name] = []
        self.app_name_to_sids[app_name].append(sid)
        for d in data['subscriptions']:
            self.add_subscription(sid, d)

    def on_unsubscribe(self, sid, data):
        self.log(f"client {data['app_name']} leaved rooms {data['subscriptions']}")
        for d in data['subscriptions']:
            self.remove_subscription(sid, d)

    async def on_client_notification(self, sid, data):
        """
        client_notifications are forwarded by Router from providers
        to subscribers via corresponding rooms, where a room is a property name.
        data: dict(name=prop_name, value=prop_value)
        """
        no_logging = data.get('no_logging', False)
        no_data_logging = data.get('no_data_logging', False)
        if no_logging:
            pass
        elif no_data_logging:
            self.log(f"{data['name']}: ...")
        else:
            self.log(f"{data['name']}:", data.get('value'))

        subscription = data['name']
        if subscription not in self.subscription_sids:
            self.log(f"{subscription}: no handlers - notification dropped.")
            return

        if 'cookies' not in data['value']:
            data['value']['cookies'] = dict(src_sid=[])

        cookies = data['value']['cookies']
        src_sids = cookies['src_sid']
        # sids are added to the cookies only by this procedure
        src_sids.append(sid)
        # shuffle for naive balance loading in case of twin services
        subscription_sids = deepcopy(self.subscription_sids[subscription])
        random.shuffle(subscription_sids)
        # do not forward notification to self and self twins
        the_twin_app_sids = self.app_name_to_sids[self.sid_to_app[sid]['name']]
        for s in the_twin_app_sids:
            try:
                subscription_sids.remove(s)
            except:
                # self may not be subscribed to this notification: ignore
                pass
        # when service is the owner of the first notification, it notifies all twins,
        # else client always notifies only one of the twins
        if not ( len(src_sids) == 1 and self.sid_to_app[sid]['type'] == 'service' ):
            # only one twin app gets notified
            subscription_sids = self.remove_twin_app_sids(subscription_sids, src_sids)
        for target_sid in subscription_sids:
            sent_to = len(src_sids) * '>'
            self.log(f"{subscription}: {self.sid_to_app[sid]['name']} {sent_to} {self.sid_to_app[target_sid]['name']}")
            room = f"{subscription}_{target_sid}"
            await self.emit(subscription, data['value'], room=room)


    def remove_twin_app_sids(self, sids, sids_to_stay):
        """
           Remove socket_ids of twin applications from sids array;
           If sids_to_stay contain the twin app socket_id, then leave
           it in resulting array and remove the twin sid.
        """
        res = []
        for s in sids_to_stay:
            if s in sids:
                res.append(s)
                self.remove_sid_with_twins(sids, s)
        while sids:
            res.append(sids[0])
            self.remove_sid_with_twins(sids, sids[0])
        return res


    def remove_sid_with_twins(self, sids, sid_to_remove):
        twin_sids_to_remove = self.app_name_to_sids[self.sid_to_app[sid_to_remove]['name']]
        for s in twin_sids_to_remove:
            sids.remove(s)
