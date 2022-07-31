import { api, apiLog } from '$api';

const HANDLER_PREFIX = 'on';

export default async function apiPlugin(store) {

    // REGISTER EVENT HANDLERS

    let handlers = Object.keys(store._actions)
        .filter(path => getAction(path).startsWith(HANDLER_PREFIX))
        .map(path => ({ [getEvent(path)]: path }))
        .reduce((prev, curr) => ({ ...prev, ...curr }), {});

    // react to events using handlers if they exist
    api.socket.onAny((event, ...args) => {
        apiLog(`${event} event detected`, args)
        if (event in handlers) {
            store.dispatch(handlers[event], args);
        }

    });

    apiLog('registered event handlers', handlers);

    // CREATE STORE MODULE

    store.registerModule('api', {
        namespaced: true,
        state: {
            ...api
        },
    })

    apiLog('registered api store module');

    // LOAD INITIAL DATA

    store.dispatch('app/load')

    apiLog('loaded root data');
}

// path parsing

function getAction(path) {
    const pathItems = path.split('/');
    const action = pathItems[pathItems.length - 1];
    return action;
}

function getEvent(path) {
    const action = getAction(path);
    const actionWithoutPrefix = action.replace(HANDLER_PREFIX, "");
    return toSnakeCase(actionWithoutPrefix);
}

// case conversion

function toSnakeCase(string) {
    let s = string[0].toLowerCase() + string.slice(1);
    return s
        .replaceAll("/", "_") // replace path seperator / with _
        .replaceAll(/[A-Z]/g, // replace camelCase with snake_case
            letter => `_${letter.toLowerCase()}`
        )
}
