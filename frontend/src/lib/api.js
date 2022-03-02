import Vue from 'vue'
import Vuex from 'vuex'
import createLogger from 'vuex/dist/logger'

const io = require("socket.io-client");
const _ = require('underscore');

import { deepFind, deepGet, deepSet } from "./store"
import { readDotenv, writeDotenv } from './env';

export function createConnectedStore(rawStoreConfig) {
    let canonicalStoreConfig = makeCanonicalConfig(rawStoreConfig);
    Vue.use(Vuex);
    return new Vuex.Store({
        state: {
            ...canonicalStoreConfig.state,
            ...apiGatewayStoreMixin.state,
        },
        mutations: {
            ...canonicalStoreConfig.mutations,
            ...apiGatewayStoreMixin.mutations,
        },
        actions: {
            ...canonicalStoreConfig.actions,
            ...apiGatewayStoreMixin.actions,
        },
        getters: {
            ...canonicalStoreConfig.getters,
            ...apiGatewayStoreMixin.getters,
        },
        modules: {
            ...canonicalStoreConfig.modules,
            ...apiGatewayStoreMixin.modules,
        },
        plugins: [
            ...canonicalStoreConfig.plugins,
            ...apiGatewayStoreMixin.plugins,
        ]
    });
}

export function createConnectedModule(apiConfig, rawModuleConfig = {}) {
    let connectedModuleMixin = createApiModuleMixin(apiConfig);
    let canonicalModuleConfig = makeCanonicalConfig(rawModuleConfig);
    return {
        state: {
            ...canonicalModuleConfig.state,
            ...connectedModuleMixin.state,
        },
        mutations: {
            ...canonicalModuleConfig.mutations,
            ...connectedModuleMixin.mutations,
        },
        actions: {
            ...canonicalModuleConfig.actions,
            ...connectedModuleMixin.actions,
        },
        getters: {
            ...canonicalModuleConfig.getters,
            ...connectedModuleMixin.getters,
        },
        modules: {
            ...canonicalModuleConfig.modules,
            ...connectedModuleMixin.modules,
        },
    }
}

export function createApiModuleMixin({ apiName = null, apiUrl = null }) {
    return makeCanonicalConfig({
        state: {
            api: null,
            apiConnected: false,
            apiName,
            apiUrl,
            $apiServiceError: "",
        },
        mutations: {
            apiChangeUrl(state, { url }) {
                state.apiUrl = url;
                state.api.reconnect({ url })
            }
        },
    });
}

const rootApiMixin = createApiModuleMixin({
    apiName: 'root'
})

const apiGatewayStoreMixin = {
    state: {
        dotenv: null,
        apiGatewayStatus: null,
        apiGatewayPaths: [],
        ...rootApiMixin.state
    },
    mutations: {
        // load the .env file into the store
        readDotenv(state) {
            gatewayLogGroup("Reading dotenv file")
            let dotenv = readDotenv();
            gatewayLog("Loaded dotenv file:", dotenv)
            state.dotenv = dotenv;
            gatewayLog("Saved dotenv file to state.dotenv");
            gatewayLogGroupEnd();
        },
        // save the .env file to disk
        // TODO - ensure consistancy with apiUrl parameter
        writeDotenv(state) {
            gatewayLogGroup("Writing dotenv file");
            let dotenv = state.dotenv;
            gatewayLog("Loaded dotenv state:", dotenv)
            writeDotenv(dotenv);
            gatewayLog("Saved dotenv state to .env file");
            gatewayLogGroupEnd();

        },
        // initialize root API url
        initRootApiUrl(state) {
            gatewayLogGroup("Initalizing root API url");
            let apiUrl = state.dotenv.protocol
                + "//" + state.dotenv.host
                + ":" + state.dotenv.port;
            gatewayLog("Constructed apiUrl:", apiUrl);
            state.apiUrl = apiUrl;
            gatewayLog("Saved apiUrl to state.apiUrl");
            gatewayLogGroupEnd();
        },
        initApiGatewayPaths(state) {
            state.apiGatewayPaths = deepFind(state)
                .filter((path) => path.endsWith("api"));
        },
        // initialize an API object from parameters
        initApi(state, { apiPath }) {
            let apiParams = {
                name: deepGet(state, apiPath + 'Name'),
                url: deepGet(state, apiPath + 'Url'),
            }
            deepSet(state, apiPath, new Api(apiParams));
        },
        // set API gateway status
        setApiGatewayStatus(state, { status }) {
            state.apiGatewayStatus = status;
        },
        // assign a value to a deep path
        setPath(state, { path, value }) {
            // but only if the value changed
            if (!_.isEqual(deepGet(state, path), value)) {
                deepSet(state, path, value);
            }
        },
        ...rootApiMixin.mutations
    },
    actions: {
        // initialize the API objects to any store path 
        // ending with 'api' using its previous value as the
        // initialization parameters
        async initApis({ state, commit, dispatch }) {
            commit('initApiGatewayPaths');
            for (let apiPath of state.apiGatewayPaths) {
                await dispatch('initApi', { apiPath });
            }
            commit('setApiGatewayStatus', { status: 'initialized' });
        },
        async initApi({ state }, { apiPath }) {
            let api = await new Api({
                name: deepGet(state, apiPath + 'Name'),
                url: deepGet(state, apiPath + 'Url'),
            })
            await deepSet(state, apiPath, api);
            await api.connect();
        },
        changeRootApiUrl({ commit }, { url }) {
            commit('apiChangeUrl', { url })
            commit('writeDotenv')
        },
        ...rootApiMixin.actions
    },
    getters: {
        // get a value from a deep path
        getPath: (state, getters, rootState) => (path) => {
            return deepGet(rootState, path);
        },
        // get full root store
        getRootState(state, getters, rootState) {
            return rootState;
        },
        ...rootApiMixin.getters
    },
    plugins: [
        createApiGatewayPlugin(),
        createLogger({
            filter(mutation) {
                let hiddenMutationTypes = [
                    //'setPath',
                    'ui/key/activate',
                    'ui/key/deactivate',
                    'workspace/target/selectionSet',
                    'workspace/sample/selectionSet',
                ]
                return !hiddenMutationTypes.includes(mutation.type)
            },
        }),
        ...rootApiMixin.plugins
    ]
};

// This is called immediately after the store is initialized
function createApiGatewayPlugin() {
    return store => {
        /**
         *      INITIALIZE STATE
         *      Load configs and init API sockets
         */

        gatewayLog('Initializing state');

        // Load dotenv and build API URL
        store.commit('readDotenv');
        store.commit('initRootApiUrl');

        // Init all API instances / namespaces in the store
        store.dispatch('initApis').then(() => {
            /**
             *      BIND VARIABLES
             *      Reactively bind all state variables starting with $
             */
            gatewayLog("Finding variables to bind...");
            // Identify variables to bind
            let toBind = deepFind(store.state)
                .filter((path) => (pathType(path) === 'boundVariable'))
                .map((path) => ({ path, name: pathToSnakeCase(path) }));

            if (toBind.length > 0) {
                gatewayLogGroup(`Binding ${toBind.length} variables`);
                gatewayLog('Variables to bind: ', toBind);
                // Bind variables to the backend using a two-way 
                // reactive variable binding
                for (let { path, name } of toBind) {
                    gatewayLog('Binding', path, `(${name})`)
                    // Get the appropriate API
                    let api = getApi(store, path);
                    // Backend Reacts to Frontend Changes
                    store.watch(
                        (state, getters) => (getters.getPath(path)),
                        (value) => {
                            api.set({ name, value })
                        }
                    );
                    // Frontend Reacts to Backend Changes
                    // Pass the setPath mutation commit as a callback
                    // allowing the backend to write to the variable reactively
                    api.bind({
                        name,
                        callback: (payload) => {
                            store.commit('setPath', {
                                path,
                                value: payload.value
                            });
                        }
                    });
                }
                gatewayLogGroupEnd();
            } else {
                gatewayLog("Found no variables to bind.")
            }

            /**
             *      SYNC ROOMS
             *      Reactively enter and leave rooms 
             *      using state variables starting with $room
             */

            gatewayLog("Finding rooms to sync...")
            // Identify rooms to sync
            let toSync = deepFind(store.state)
                .filter((path) => (pathType(path) === 'room'))
                .map((path) => ({ path, rooms: deepGet(store.state, path) }));

            if (toSync.length > 0) {
                let s = toSync.length > 1 ? 's' : '';
                gatewayLogGroup(`Syncing ${toSync.length} room${s}`);
                gatewayLog(`Room${s} to sync:`, toSync);
                // Initialize rooms
                for (let { path, rooms } of toSync) {
                    // Get the appropriate API
                    let api = getApi(store, path);
                    // Initialize subscriptions
                    api.enter(rooms);
                    // Make rooms reactive
                    store.watch(
                        (state, getters) => (getters.getPath(path)),
                        (newValue, oldValue) => {
                            if (!_.isEqual(newValue, oldValue)) {
                                api.leave(oldValue);
                                api.enter(newValue);
                            }
                        }
                    );
                }
                gatewayLogGroupEnd();
            } else {
                gatewayLog("Found no rooms to sync.")
            }

            /**
             *      DECLARE ENDPOINTS
             *      Declare endpoints using state variables 
             *      starting with $endpoint
             */

            gatewayLog("Finding endpoints to declare...")
            // Identify endpoints to declare
            let toDeclare = deepFind(store.state)
                .filter((path) => (pathType(path) === 'endpoint'))
                .map((path) => ({ path, endpoints: deepGet(store.state, path) }));

            if (toDeclare.length > 0) {
                let s = toDeclare.length > 1 ? 's' : '';
                gatewayLogGroup(`Declaring ${toDeclare.length} endpoint${s}`);
                gatewayLog(`Endpoint${s} to declare:`, toDeclare);
                // Initialize subscriptions
                for (let { path, endpoints } of toDeclare) {
                    // Get the appropriate API
                    let api = getApi(store, path);
                    // Declare endpoints
                    api.declare(endpoints);
                }
                gatewayLogGroupEnd();
            } else {
                gatewayLog("Found no endpoints to declare.")
            }
        });
    }
}

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


// Helper functions

function getApi(store, path) {
    // Check if the module of the variable to be bound 
    // contains its own dedicated API instance and namespace
    let nearestApiPath = path
        .split("/").slice(0, -1)
        .concat("api").join("/");
    let nearestApi = store.getters.getPath(nearestApiPath);
    let rootApi = store.getters.getPath("api");
    // Use nearest API if it exists, and default to the root
    // API instance and namespace otherwise
    return nearestApi || rootApi;
}

export function pathToSnakeCase(path) {
    return path
        .replaceAll("$", "")  // remove bound variable symbol $
        .replaceAll("/", "_") // replace path seperator / with _
        .replaceAll(/[A-Z]/g, // replace camelCase with snake_case
            letter => `_${letter.toLowerCase()}`
        )
}

export function pathToCamelCase(path) {
    return path
        .replaceAll("$", "")  // remove bound variable symbol $
        .split("/")           // split words by path symbol /
        .map(                 // capitalize first letters
            word => word[0].toUpperCase() + word.substring(1)
        )
        .join("")             // combine to a single string
        .replace(/^[A-Z]/,    // lower the case of the first letter
            firstChar => firstChar.toLowerCase()
        )
}

function makeCanonicalConfig(storeConfig) {
    return Object.assign({}, {
        state: {},
        mutations: {},
        actions: {},
        getters: {},
        plugins: [],
    }, storeConfig);
}

function pathType(path) {
    if (path.includes('$room')) return 'room';
    if (path.includes('$endpoint')) return 'endpoint';
    if (path.includes('$')) return 'boundVariable';
    //else
    return 'localVariable';
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

let gatewayLogPrefix = '[Gateway]';

function gatewayLog(...args) {
    console.log(gatewayLogPrefix, ...args)
}

function gatewayLogGroup(...args) {
    console.groupCollapsed(gatewayLogPrefix, ...args)
}

function gatewayLogGroupEnd() {
    console.groupEnd();
}