import * as _ from "underscore";

import { Api } from "./socket"
import pathlib from "./path"
import { createApiModuleMixin } from './store';


const rootApiMixin = createApiModuleMixin({
    apiName: 'root'
})

export const apiGatewayStoreMixin = {
    state: {
        apiGatewayStatus: null,
        apiGatewayPaths: [],
        apiEventCache: [],
        ...rootApiMixin.state
    },
    mutations: {
        // initialize root API url
        initRootApiUrl(state) {
            gatewayLogGroup("Initalizing root API url");
            let apiUrl = "http://127.0.0.1:5010"
            gatewayLog("Constructed apiUrl:", apiUrl);
            state.apiUrl = apiUrl;
            gatewayLog("Saved apiUrl to state.apiUrl");
            gatewayLogGroupEnd();
        },
        initApiGatewayPaths(state) {
            state.apiGatewayPaths = pathlib.find(state)
                .filter((path) => path.endsWith("api"));
        },
        // initialize an API object from parameters
        initApi(state, { apiPath }) {
            let apiParams = {
                name: pathlib.get(state, apiPath + 'Name'),
                url: pathlib.get(state, apiPath + 'Url'),
            }
            pathlib.set(state, apiPath, new Api(apiParams));
        },
        // set API gateway status
        setApiGatewayStatus(state, { status }) {
            state.apiGatewayStatus = status;
        },
        // assign a value to a deep path
        setPath(state, { path, value }) {
            // but only if the value changed
            if (!_.isEqual(pathlib.get(state, path), value)) {
                pathlib.set(state, path, value);
            }
        },
        // event cache
        eventCacheAdd(state, response) {
            state.apiEventCache.push(response);
        },
        eventCacheRemove(state, response) {
            let responseIndex = state.apiEventCache.indexOf(response);
            state.apiEventCache.splice(responseIndex, 1);
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
                name: pathlib.get(state, apiPath + 'Name'),
                url: pathlib.get(state, apiPath + 'Url'),
            })
            await pathlib.set(state, apiPath, api);
            await api.connect();
        },
        changeRootApiUrl({ commit }, { url }) {
            commit('apiChangeUrl', { url })
        },
        ...rootApiMixin.actions
    },
    getters: {
        // get a value from a deep path
        getPath: (state, getters, rootState) => (path) => {
            return pathlib.get(rootState, path);
        },
        // get full root store
        getRootState(state, getters, rootState) {
            return rootState;
        },
        // event cache
        eventCacheHit: (state) => (response) => {
            return state.apiEventCache.indexOf(response) > -1;
        },
        ...rootApiMixin.getters
    },
    plugins: [
        createApiGatewayPlugin(),
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

        // Get API URL
        store.commit('initRootApiUrl');

        // Init all API instances / namespaces in the store
        store.dispatch('initApis').then(() => {
            /**
             *      BIND VARIABLES
             *      Reactively bind all state variables starting with $
             */
            gatewayLog("Finding variables to bind...");
            // Identify variables to bind
            let toBind = pathlib.find(store.state)
                .filter((path) => (pathlib.type(path) === 'boundVariable'))
                .map((path) => ({ path, name: pathlib.toSnakeCase(path) }));

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
                            // check cache to prevent backend responses
                            // being echoed back to the backend
                            let cached = store.getters['eventCacheHit'](value);
                            if (!cached) {
                                // emit the event if not cached
                                api.set({ name, value });
                            } else {
                                // otherwise remove the event from the cache
                                // since it has been handled so no need to 
                                // waste memory on it
                                store.commit('eventCacheRemove', value);
                            }
                        }
                    );
                    // Frontend Reacts to Backend Changes
                    // Pass the setPath mutation commit as a callback
                    // allowing the backend to write to the variable reactively
                    api.bind({
                        name,
                        callback: (payload) => {
                            // cačhe backend events in order
                            // to prevent echoes
                            store.commit('eventCacheAdd', payload.value);
                            // write the event to the path
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
            let toSync = pathlib.find(store.state)
                .filter((path) => (pathlib.type(path) === 'room'))
                .map((path) => ({ path, rooms: pathlib.get(store.state, path) }));

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
            let toDeclare = pathlib.find(store.state)
                .filter((path) => (pathlib.type(path) === 'endpoint'))
                .map((path) => ({ path, endpoints: pathlib.get(store.state, path) }));

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

// helpers

function getApi(store, path) {
    let apiRelativePath = "api";
    // Check if the module of the variable to be bound 
    // contains its own dedicated API instance and namespace
    let nearestApiPath = path
        .split("/").slice(0, -1)
        .concat(apiRelativePath).join("/");
    let nearestApi = store.getters.getPath(nearestApiPath);
    let rootApi = store.getters.getPath(apiRelativePath);
    // Use nearest API if it exists, and default to the root
    // API instance and namespace otherwise
    return nearestApi || rootApi;
}

// logging 

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