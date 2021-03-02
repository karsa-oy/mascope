const _ = require('underscore');
const fs = require('fs');
const envfile = require('envfile');

var external_notifications = [];

export class BECom {
    constructor(ctx) {
        this.ctx = ctx;
        this.log_prefix = ctx.$options.name;
    }

    subscribe(room=null) {
        let the_room = room || this.ctx.room || this.ctx.socket.id;
        this.ctx.socket.emit('subscribe',
                         {'app_name': this.ctx.$options.name,
                          'endpoints': this.ctx.endpoints,
                          'room': the_room});
        this.log(the_room, 'subscribed for', this.ctx.endpoints);
        this.ctx.socket.emit('client_notification', {'name': 'service_state', 'value': {}, 'room': the_room});
    }
    
    unsubscribe(room=null) {
        let the_room = room || this.ctx.room || this.ctx.socket.id;
        this.ctx.socket.emit('unsubscribe',
                         {'app_name': this.ctx.$options.name,
                          'endpoints':this.ctx.endpoints,
                          'room': the_room});
        this.log(the_room, 'unsubscribed from', this.ctx.endpoints);
    }
    
    export_one_way_binding_prop(name, new_value, old_value, room=null, no_logging=false) {
        if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            let the_room = room || this.ctx.room || this.ctx.socket.id;
            if ( no_logging === false ) {
                this.log('send', name, 'to', the_room, old_value, new_value);
            }
            this.ctx.socket.emit('client_notification',
                            {'name': name, 'value': new_value, 'room': the_room});
    }
    
    export_two_way_binding_prop(name, new_value, old_value, room=null, no_logging=false) {
            if ( _.isEqual(new_value, old_value) ) {
                return false;
            }
            let the_room = room || this.ctx.room || this.ctx.socket.id;
            let i = external_notifications.findIndex(
                        (e) => _.isEqual(e, [name, new_value]))
            if ( i === -1 ) {
                if ( no_logging === false )
                this.log('send', name, 'to', the_room, old_value, new_value);
                this.ctx.socket.emit('client_notification',
                                {'name': name, 'value': new_value, 'room': the_room});
            } else {
                external_notifications.splice(i, 1);
            }
    }
    
    import_one_way_binding_prop(name, value, no_logging=false) {
            if ( _.isEqual(value, this.ctx[name]) ) {
                return;
            }
            if ( no_logging === false ) {
                this.log("receive", name, value);
            }
            this.ctx[name] = value;
    }
    
    import_two_way_binding_prop(name, value, no_logging=false) {
            if ( _.isEqual(value, this.ctx[name]) ) {
                return;
            }
            if ( no_logging === false ) {
                this.log("receive", name, value);
            }
            external_notifications.push([name, value]);
            this.ctx[name] = value;
    }
    
    log(...args) {
        console.log('[' + this.log_prefix + ']',  ...args);
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