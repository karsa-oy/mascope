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