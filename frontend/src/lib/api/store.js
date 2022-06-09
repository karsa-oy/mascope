import Vue from 'vue';
import Vuex from 'vuex';
import path from "./path";

import { apiGatewayStoreMixin } from './gateway';

export function createConnectedStore(rawStoreConfig) {
    let canonicalStoreConfig = makeCanonicalConfig(rawStoreConfig);
    Vue.use(Vuex);
    let store = new Vuex.Store({
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
    let watchers = path.find(rawStoreConfig)
        .filter(p => p.endsWith("watchers"))
        .map(p => path.get(rawStoreConfig, p))
        .reduce((prev, next) => ({ ...prev, ...next }), {});
    Object.entries(watchers).forEach(
        ([target, action]) => {
            let fn = target in store.getters
                ? () => store.getters[target]
                : (state) => path.get(state, target);
            let callback = () => store.dispatch(action);
            store.watch(fn, callback);
        }
    )
    let subs = path.find(rawStoreConfig)
        .filter(p => p.endsWith("subs"))
        .map(p => path.get(rawStoreConfig, p))
        .reduce((prev, next) => {
            let keys = Object.keys(prev)
                .concat(Object.keys(next));
            let result = {};
            for (let key of keys) {
                let prevVals =
                    key in prev ? prev[key] : [];
                let nextVals =
                    key in next ? next[key] : [];
                result[key] = prevVals.concat(nextVals);
            }
            return result;
        }, {});
    Object.entries(subs).forEach(
        ([mutationType, actions]) => {
            let callback = (payload) => {
                actions.forEach((action) => {
                    store.dispatch(action, {
                        payload,
                        mutation: mutationType
                    });
                });
            }
            store.subscribe((mutation) => {
                if (mutation.type == mutationType) {
                    callback(mutation.payload);
                }
            });
        }
    )
    return store;
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

export function makeCanonicalConfig(storeConfig) {
    return Object.assign({}, {
        state: {},
        mutations: {},
        actions: {},
        getters: {},
        plugins: [],
    }, storeConfig);
}