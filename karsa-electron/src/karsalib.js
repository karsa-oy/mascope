const _ = require('underscore');
const fs = require('fs');
const envfile = require('envfile');
const io = require("socket.io-client");

const NO_LOGGING_DEFAULT = false;
const NO_DATA_LOGGING_DEFAULT = true;


export class BECom {
    constructor(ctx) {
        this.ctx = ctx;
        this.log_prefix = ctx.$options.name;
        this.external_notifications = [];
    }

    connect(url=null) {
        let the_url = url || this.ctx.url;
        this.log(this.ctx.$options.name, "Connecting to url: ", the_url);
        let namespace = io.connect(the_url);
        namespace.on("connect", () => {
            this.ctx['global_namespace_connected'] = true;
            // handlers for for external notifications (endpoint imports), if any:
            this.ctx['sid'] = namespace.id;
            this.subscribe(this.ctx.sid, namespace);
        });
        // no need to unsubscribe on disconnect - client is unsubscribed by framework
        namespace.on("disconnect", () => {
            this.ctx['global_namespace_connected'] = false;
            this.log(this.ctx.$options.name, "socket disconnected");
        });
        return namespace
    }

    disconnect(namespace=null) {
        let the_namespace = namespace || this.ctx.global_namespace;
        if (the_namespace && the_namespace.connected) {
            the_namespace.disconnect();
        }
    }

    subscribe(room=null, namespace=null) {
        let the_room = room || this.ctx.room;
        let the_namespace = namespace || this.ctx.global_namespace;
        this.log(the_room, 'subscribed for', this.ctx.endpoints);
        if ( !the_room )
            throw "Subscribe error: no room.";
        the_namespace.emit('subscribe',
                         {'app_name': this.ctx.$options.name,
                          'endpoints': this.ctx.endpoints,
                          'room': the_room});
        the_namespace.emit('client_notification',
                             {'name': 'service_state',
                              'value': {},
                              'room': the_room
                              });
    }
    
    unsubscribe(room=null, namespace=null) {
        let the_room = room || this.ctx.room;
        let the_namespace = namespace || this.ctx.global_namespace;
        this.log(the_room, 'unsubscribed from', this.ctx.endpoints);
        if ( !the_room )
            throw "Unsubscribe error: no room.";
        the_namespace.emit('unsubscribe',
                         {'app_name': this.ctx.$options.name,
                          'endpoints':this.ctx.endpoints,
                          'room': the_room});
    }
    
    export_one_way_binding_prop(name,
                                new_value,
                                old_value,
                                room=null,
                                namespace=null,
                                no_logging=NO_LOGGING_DEFAULT,
                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                ) {
        if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            let the_room = room || this.ctx.room || this.ctx.sid;
            let the_namespace = namespace || this.ctx.global_namespace;
            if ( no_logging === false ) {
                this.log('send', name, 'to', the_room, old_value, new_value);
            }
            the_namespace.emit('client_notification',
                            {name: name, value: new_value, room: the_room,
                             no_logging: no_logging, no_data_logging: no_data_logging});
    }
    
    export_two_way_binding_prop(name,
                                new_value,
                                old_value,
                                room=null,
                                namespace=null,
                                no_logging=NO_LOGGING_DEFAULT,
                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                ) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            let the_room = room || this.ctx.room || this.ctx.sid;
            let the_namespace = namespace || this.ctx.global_namespace;
            let i = this.external_notifications.findIndex(
                        (e) => _.isEqual(e, [name, new_value]))
            if ( i === -1 ) {
                if ( no_logging === false )
                this.log('send', name, 'to', the_room, old_value, new_value);
                the_namespace.emit('client_notification',
                                {name: name, value: new_value, room: the_room,
                                 no_logging: no_logging, no_data_logging: no_data_logging});
            } else {
                this.external_notifications.splice(i, 1);
            }
    }
    
    import_one_way_binding_prop(name, value, no_logging=NO_LOGGING_DEFAULT) {
            if ( _.isEqual(value, this.ctx[name]) ) {
                return;
            }
            if ( no_logging === false ) {
                this.log("receive", name, value);
            }
            this.ctx[name] = value;
    }
    
    import_two_way_binding_prop(name, value, no_logging=NO_LOGGING_DEFAULT) {
            if ( _.isEqual(value, this.ctx[name]) ) {
                return;
            }
            if ( no_logging === false ) {
                this.log("receive", name, value);
            }
            this.external_notifications.push([name, value]);
            this.ctx[name] = value;
    }
    
    log(...args) {
        console.log('[' + this.log_prefix + ']',  ...args);
    }

    emit_client_notification(name,
                             value,
                             room=null,
                             namespace=null,
                             no_logging=NO_LOGGING_DEFAULT,
                             no_data_logging=NO_DATA_LOGGING_DEFAULT
                             ) {
        let the_room = room || this.ctx.room || this.ctx.socket.id;
        let the_namespace = namespace || this.ctx.global_namespace;
        if ( no_logging ) {
            // pass;
        }
        else if ( no_data_logging ) {
            this.log(name, '...', 'to room', the_room);
        }
        else {
            this.log(name, ':', value, 'to room', the_room);
        }
        the_namespace.emit('client_notification',
                            {name: name,
                             value: value,
                             room: the_room,
                             no_logging: no_logging,
                             no_data_logging: no_data_logging
                            });
    }
}

export function read_dotenv() {
        let dotenv = {};
        let env_string = fs.readFileSync('.env');
        let env_parsed = envfile.parse(env_string);
        for (var key in env_parsed){
            var key_val = {}
            key_val[key] = env_parsed[key];
            Object.assign(dotenv, key_val);
        }
        return dotenv
}

export function write_dotenv(dotenv) {
        let env_string = envfile.stringify(dotenv);
        fs.writeFileSync('.env', env_string);
}