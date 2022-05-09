const io = require("socket.io-client");

export class Api {
    constructor({
        name = null,
        url = null,
        onConnect = () => { },
        onDisconnect = () => { },
    }) {
        this.name = name;
        this.url = url;
        this.connected = false;
        this.onConnect = onConnect;
        this.onDisconnect = onDisconnect;
    }

    async connect() {
        this.log("Connecting to url: ", this.url);
        this.socket = await io.connect(this.url);
        this.log("API connected");
        this.socket.on("connect", () => {
            this.log("Socket connected");
            this.enter(this.socket.id)
                .then(() => {
                    this.connected = true;
                    this.onConnect();
                })
        });
        this.socket.on("disconnect", () => {
            this.log("Socket disconnected");
            this.leave(this.socket.id)
                .then(() => {
                    this.connected = false;
                    this.onDisconnect();
                })
        });
    }

    async disconnect() {
        if (this.socket && this.socket.connected) {
            await this.socket.disconnect();
        }
    }

    reconnect(newUrl) {
        this.disconnect();
        this.url = newUrl;
        this.connect();
    }

    declare(endpoints) {
        let endpointsArray = coerceArray(endpoints);
        this.log('declaring endpoints', endpointsArray.join(", "));
        this.socket.emit('declare_endpoints', {
            'app_name': this.name,
            'endpoints': endpointsArray
        });
    }

    async enter(rooms) {
        if (!rooms || rooms.length == 0) return;
        let roomsArray = coerceArray(rooms);
        this.log(`entering room${roomsArray.length > 1 ? 's' : ''}`, roomsArray.join(", "));
        for (let room of roomsArray) {
            this.socket.emit('enter_room', {
                'app_name': this.name,
                'room': room
            });
        }
    }

    async leave(rooms) {
        if (!rooms || rooms.length == 0) return;
        let roomsArray = coerceArray(rooms);
        this.log(`leaving room${roomsArray.length > 1 ? 's' : ''}`, roomsArray.join(", "));
        for (let room of roomsArray) {
            this.socket.emit('leave_room', {
                'app_name': this.name,
                'room': room
            });
        }
    }

    set({
        name,
        value,
        room = null,
        requestId = Math.random().toString(36).substring(2),
        loggingLevel = this.loggingLevel,

    }) {
        this.socket.emit('client_notification', {
            name,
            value,
            room,
            request_id: requestId,
            no_logging: loggingLevel == 'none',
            no_data_logging: loggingLevel == 'basic',
            client_room: this.socket.id,
        })
    }

    call({
        endpoint,
        onSuccess = () => { },
        onFailure = () => { },
        timeout = 5000,
        clientTimeout = timeout,
        room = null,
        client_room = this.socket.id,
        requestId = Math.random().toString(36).substring(2),
        loggingLevel = this.loggingLevel,
    }, ...values) {

        // response handler
        let handler = (response) => {
            if (response.type == 'success') {
                try {
                    onSuccess(response.body);
                } catch (error) {
                    console.error(
                        `Encountered frontend exception while calling async call onSuccess handler;`,
                        { endpoint, onSuccess, response, error }
                    )
                }
            } else if (response.type == 'failure') {
                console.error(
                    `Encountered backend exception while performing async call;`,
                    { endpoint, values, response }
                );
                try {
                    onFailure(response.body);
                } catch (error) {
                    console.error(
                        `Encountered backend exception while calling async call onFailure handler;`,
                        { endpoint, onFailure, response, error }
                    );
                }
            }
        }
        // make calls
        let makeCall = (value) => {
            let notifyCall = (resolve, reject) => {
                this.socket
                    .emit('client_notification', {
                        name: endpoint,
                        value,
                        room,
                        timeout,
                        request_id: requestId,
                        no_logging: loggingLevel == 'none',
                        no_data_logging: loggingLevel == 'basic',
                        client_room,
                    }, (response) => {
                        resolve(response)
                    });
                setTimeout(
                    () => reject(Error("Clientside socket timed out")),
                    clientTimeout
                );
            }
            return new Promise(notifyCall);
        }
        let calls = values.map((value) => () => makeCall(value));
        let firstCall = calls.shift();

        return new Promise((resolve, reject) => {
            calls
                .reduce(
                    (promise, fn) => {
                        // intermediate calls handled here
                        return promise.then((result) => {
                            handler(result);
                            return fn(result);
                        });
                    },
                    firstCall() // first call is made seperately
                )
                .then((result) => {
                    // a handler can be called to process the final result
                    handler(result);
                    resolve();
                })
                .catch((error) => {
                    // errors handled here
                    console.error(
                        `Encountered a frontend exception while performing async call;`,
                        { endpoint, values, error }
                    );
                    reject();
                });
        });
    }

    bind({ name, callback }) {
        this.socket.on(name, callback)
    }

    notify({
        name,
        value,
        room = null,
        requestId = null,
        loggingLevel = this.loggingLevel
    }) {
        this.socket.emit('client_notification', {
            name,
            value,
            room,
            request_id: requestId,
            no_logging: loggingLevel == 'none',
            no_data_logging: loggingLevel == 'basic',
            client_room: this.socket.id,
        })
    }

    log(...args) {
        let name = this.name[0].toUpperCase() + this.name.slice(1);
        console.log('[' + name + ' API]', ...args);
    }
}

function coerceArray(value) {
    let message = "Must be of type String or Array of Strings";
    let allStrings;
    switch (typeof value) {
        case 'string':
            return [value];
        case 'object':
            allStrings = value
                .every(item => (typeof item == 'string'));
            if (allStrings) {
                return value;
            } else {
                throw Error(message);
            }
        default:
            throw Error(message);
    }
}
