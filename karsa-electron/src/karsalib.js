const _ = require('underscore');
const fs = require('fs');
const envfile = require('envfile');
const io = require("socket.io-client");

const NO_LOGGING_DEFAULT = false;
const NO_DATA_LOGGING_DEFAULT = true;


export class BECom {
    constructor(ctx) {
        this.ctx = ctx;
        this.app_name = ctx.$options.name || ctx.name;
        this.external_notifications = [];
    }

    connect(url=null) {
        let the_url = url || this.ctx.url;
        this.log("Connecting to url: ", the_url);
        let namespace = io.connect(the_url);
        this.ctx['namespace'] = namespace;
        namespace.on("connect", () => {
            // handlers for for external notifications (endpoint imports), if any:
            this.ctx['room_sid'] = namespace.id;
        });
        // no need to unsubscribe on disconnect - client is unsubscribed by framework
        namespace.on("disconnect", () => {
            this.log("socket disconnected");
        });
        return namespace
    }

    disconnect(namespace=null) {
        let the_namespace = namespace || this.ctx.namespace;
        if (the_namespace && the_namespace.connected) {
            the_namespace.disconnect();
        }
    }

    subscribe(endpoints, room, namespace=null) {
        let the_namespace = namespace || this.ctx.namespace;
        this.log(room, 'subscribed for', endpoints);

        the_namespace.emit('subscribe',
                         {'app_name': this.app_name,
                          'endpoints': endpoints,
                          'client_room': room,
                          'room': room});
        the_namespace.emit('client_notification',
                            {'name': 'service_state',
                             'value': {},
                             'client_room': room,
                             'room': room,
                             });
    }
    
    unsubscribe(endpoints, room, namespace=null) {
        let the_namespace = namespace || this.ctx.namespace;
        this.log(room, 'unsubscribed from', endpoints);
        the_namespace.emit('unsubscribe',
                         {'app_name': this.app_name,
                          'endpoints': endpoints,
                          'room': room});
    }
    
    export_one_way_binding_prop(name,
                                new_value,
                                old_value=null,
                                src_room=null,   //client_room
                                target_room=null,
                                namespace=null,
                                no_logging=NO_LOGGING_DEFAULT,
                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                ) {
        if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
        // let the_room = client_room || this.ctx.room_sid;
        let from_room = src_room || this.ctx.room_sid;
        let to_room = target_room;

        let the_namespace = namespace || this.ctx.namespace;
        if ( no_logging === false ) {
            this.log('send', name, 'from', from_room, 'to', to_room, old_value, new_value);
        }
        the_namespace.emit('client_notification',
                           {name: name,
                            value: new_value,
                            client_room: from_room,
                            room: to_room,
                            no_logging: no_logging,
                            no_data_logging: no_data_logging
                           });
    }
    
    export_two_way_binding_prop(name,
                                new_value,
                                old_value,
                                src_room=null,   //client_room
                                target_room=null,
                                namespace=null,
                                no_logging=NO_LOGGING_DEFAULT,
                                no_data_logging=NO_DATA_LOGGING_DEFAULT
                                ) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            let from_room = src_room || this.ctx.room_sid;
            let to_room = target_room;
            let the_namespace = namespace || this.ctx.namespace;
            let i = this.external_notifications.findIndex(
                        (e) => _.isEqual(e, [name, new_value]))
            if ( i === -1 ) {
                if ( no_logging === false )
                    this.log('send', name, 'from', from_room, 'to', to_room, old_value, new_value);
                the_namespace.emit('client_notification',
                                    {name: name,
                                     value: new_value,
                                     client_room: from_room,
                                     room: to_room,
                                     no_logging: no_logging,
                                     no_data_logging: no_data_logging
                                     });
            } else {
                this.external_notifications.splice(i, 1);
            }
    }
    
    import_one_way_binding_prop(name, value, no_logging=NO_LOGGING_DEFAULT) {
            if ( no_logging === false ) {
                this.log("receive", name, value);
            }
            this.ctx[name] = value;
    }
    
    import_two_way_binding_prop(name, value, no_logging=NO_LOGGING_DEFAULT) {
            if ( no_logging === false ) {
                this.log("receive", name, value);
            }
            this.external_notifications.push([name, value]);
            this.ctx[name] = value;
    }
    
    log(...args) {
        console.log('[' + this.app_name + ']',  ...args);
    }

    emit_client_notification(name,
                            value,
                            client_room=null,     // src (client) room to pass thru notif.chain
                            room=null,            // target room
                            namespace=null,
                            no_logging=NO_LOGGING_DEFAULT,
                            no_data_logging=NO_DATA_LOGGING_DEFAULT
                            ) {
        let from_room = client_room || this.ctx.room_sid;
        let to_room = room;
        let the_namespace = namespace || this.ctx.namespace;
        if ( no_logging ) {
            // pass;
        }
        else if ( no_data_logging ) {
            this.log(name, '...', 'from', from_room, 'to', to_room);
        }
        else {
            this.log(name, ':', value, 'from', from_room, 'to', to_room);
        }
        the_namespace.emit('client_notification',
                            {name: name,
                             value: value,
                             client_room: from_room,
                             room: to_room,
                             no_logging: no_logging,
                             no_data_logging: no_data_logging
                            });
    }
}

export function shallow_copy(o) {
    let _o = JSON.stringify(o);
    if ( _.isUndefined(_o) )
        return _o;
    return JSON.parse(_o);
}

export function isValidFilename(string) {
    // Allow letters, numbers, space, underscore
    // Require at least one number or letter
    const valid_pattern = RegExp(/^[A-Za-z0-9 _]*[A-Za-z0-9][A-Za-z0-9 _]*$/);
    // Allow letters, numbers and underscore
    // const valid_pattern = RegExp(/^\w+$/);
    return valid_pattern.test(string);
}

export function makeValidFilename(string) {
    // Replace special characters with underscore
    return (string.replace(/[/|\\:*?"<>]/g, "_"));
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