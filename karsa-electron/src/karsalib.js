const _ = require('underscore');
const fs = require('fs');
const envfile = require('envfile');

export function export_one_way_binding_prop(ctx, name, new_value, old_value, no_logging=false) {
        if ( _.isEqual(new_value, old_value) ) {
            return false;
        }
        if ( no_logging === false ) {
            log('export', name, old_value, new_value);
        }
        ctx.socket.emit('client_notification',
                        {'name': name, 'value': new_value, 'room': ctx.socket.id});
}

export function export_two_way_binding_prop(ctx, name, new_value, old_value, no_logging=false) {
        if ( _.isEqual(new_value, old_value) ) {
            return false;
        }
        let i = ctx.external_notifications.findIndex(
                    (e) => _.isEqual(e, [name, new_value]))
        if ( i === -1 ) {
            if ( no_logging === false )
                log('export', name, old_value, new_value);
            ctx.socket.emit('client_notification',
                            {'name': name, 'value': new_value, 'room': ctx.socket.id});
        } else {
            ctx.external_notifications.splice(i, 1);
        }
}

export function import_one_way_binding_prop(ctx, name, value, no_logging=false) {
        if ( _.isEqual(value, ctx[name]) ) {
            return;
        }
        if ( no_logging === false ) {
            log("import", name, value);
        }
        ctx[name] = value;
}

export function import_two_way_binding_prop(ctx, name, value, no_logging=false) {
        if ( _.isEqual(value, ctx[name]) ) {
            return;
        }
        if ( no_logging === false ) {
            log("import", name, value);
        }
        ctx.external_notifications.push([name, value]);
        ctx[name] = value;
}

export function log(name, ...args) {
        console.log('[' + name + ']',  ...args);
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