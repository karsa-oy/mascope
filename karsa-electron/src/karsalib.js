const _ = require('underscore');
const fs = require('fs');
const envfile = require('envfile');

var ctx = null;
var log_prefix = 'unknown';
var external_notifications = [];

export function get_parent_context(this_ctx) {
    ctx = this_ctx;
    log_prefix = ctx.$options.name;
}

export function subscribe(room=null) {
    let the_room = room || ctx.room || ctx.socket.id;
    ctx.socket.emit('subscribe',
                     {'app_name': ctx.$options.name,
                      'endpoints': ctx.endpoints,
                      'room': the_room});
    ctx.socket.emit('client_notification', {'name': 'service_state', 'value': {}, 'room': the_room});
}

export function unsubscribe(room=null) {
    let the_room = room || ctx.room || ctx.socket.id;
    ctx.socket.emit('unsubscribe',
                     {'app_name': ctx.$options.name,
                      'endpoints':ctx.endpoints,
                      'room': the_room});
}

export function export_one_way_binding_prop(name, new_value, old_value, room=null, no_logging=false) {
    if ( _.isEqual(new_value, old_value) ) {
            return false;
        }
        let the_room = room || ctx.room || ctx.socket.id;
        if ( no_logging === false ) {
            log(the_room, 'export', name, old_value, new_value);
        }
        ctx.socket.emit('client_notification',
                        {'name': name, 'value': new_value, 'room': the_room});
}

export function export_two_way_binding_prop(name, new_value, old_value, room=null, no_logging=false) {
        if ( _.isEqual(new_value, old_value) ) {
            return false;
        }
        let the_room = room || ctx.room || ctx.socket.id;
        let i = external_notifications.findIndex(
                    (e) => _.isEqual(e, [name, new_value]))
        if ( i === -1 ) {
            if ( no_logging === false )
                log('export to ', the_room, name, old_value, new_value);
            ctx.socket.emit('client_notification',
                            {'name': name, 'value': new_value, 'room': the_room});
        } else {
            external_notifications.splice(i, 1);
        }
}

export function import_one_way_binding_prop(name, value, no_logging=false) {
        if ( _.isEqual(value, ctx[name]) ) {
            return;
        }
        if ( no_logging === false ) {
            log("import", name, value);
        }
        ctx[name] = value;
}

export function import_two_way_binding_prop(name, value, no_logging=false) {
        if ( _.isEqual(value, ctx[name]) ) {
            return;
        }
        if ( no_logging === false ) {
            log("import", name, value);
        }
        external_notifications.push([name, value]);
        ctx[name] = value;
}

export function log(...args) {
    console.log('[' + log_prefix + ']',  ...args);
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