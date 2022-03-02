import { Api } from "./api";

export function bindState(bindings) {
    let computedBindings = Object.keys(bindings)
        .map((localVariable) => {
            let path = bindings[localVariable];
            return {
                [localVariable]: {
                    get() {
                        return this.$store.getters.getPath(path);
                    },
                    set(value) {
                        this.$store.commit('setPath', { path, value })
                    }
                }
            }
        });
    return Object.assign({}, ...computedBindings);
}


/**
 * get a nested store variable with a path
 * deepGet(store, "a/b/c") is the same as
 * store['a']['b']['c']
 */
export function deepGet(store, path, sep = "/") {
    if (!path) {
        throw Error("Path must be provided");
    }
    let keys = path.split(sep);
    if (keys.length == 1) {
        return store[keys[0]];
    }
    return deepGet(store[keys[0]], keys.slice(1).join(sep));
}

/**  
 * set a nested store variable with a path
 * deepSet(store, "a/b/c", val) is the same as
 * store['a']['b']['c'] = val
 */
export function deepSet(store, path, val, sep = "/") {
    if (!path) {
        throw Error("Path must be provided");
    }
    let keys = path.split(sep);
    if (keys.length == 1) {
        store[keys[0]] = val;
    } else {
        store = store[keys[0]]
        return deepSet(store, keys.slice(1).join(sep), val);
    }
}


/**
 * find all deep paths in a store
 * and return them in a path notation
 * deepFind({'x': 1, 'a': {'b': {'c': 'foo', 'y': 'bar'}, 'z': 'baz'}})
 * returns ["x", "a/b/c", "a/b/y", "a/z"]
 */
export function deepFind(store, sep = "/") {
    let paths = [];
    for (let key in store) {
        if (key.startsWith('_')) {
            continue;
        }
        paths.push(key);
        let value = store[key];
        let isObject = value instanceof Object;
        let isArray = value instanceof Array;
        let hasKeys = isObject && !isArray ? Object.keys(value).length > 0 : false;
        let isApi = value instanceof Api;
        if (hasKeys && !isApi && !key.startsWith('$')) {
            let subkeys = deepFind(value);
            paths = paths.concat(subkeys.map(function (subkey) {
                return key + sep + subkey;
            }));
        }
    }
    return paths;
}
