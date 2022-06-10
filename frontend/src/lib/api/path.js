import { Api } from "./socket";

export default {
    // operations
    /**
     * get a nested store variable with a path
     * path.get(store, "a/b/c") is the same as
     * store['a']['b']['c']
     */
    get(store, path, sep = "/") {
        if (!path) {
            throw Error("Path must be provided");
        }
        let keys = path.split(sep);
        try {
            let result = keys.length == 1
                ? store[keys[0]]
                : this.get(store[keys[0]], keys.slice(1).join(sep), sep);
            return result;
        } catch (error) {
            throw Error(`Failed to get path ${path}`, error)
        }
    },
    /**  
     * set a nested store variable with a path
     * path.set(store, "a/b/c", val) is the same as
     * store['a']['b']['c'] = val
     */
    set(store, path, val, sep = "/") {
        if (!path) {
            throw Error("Path must be provided");
        }
        let keys = path.split(sep);
        try {
            if (keys.length == 1) {
                store[keys[0]] = val;
            } else {
                store = store[keys[0]]
                return this.set(store, keys.slice(1).join(sep), val, sep);
            }
        } catch (error) {
            throw Error(`Failed to set path ${path}`, error)
        }
    },
    /**
     * find all deep paths in a store
     * and return them in a path notation
     * path.find({'x': 1, 'a': {'b': {'c': 'foo', 'y': 'bar'}, 'z': 'baz'}})
     * returns ["x", "a/b/c", "a/b/y", "a/z"]
     */
    find(store, sep = "/") {
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
                let subkeys = this.find(value, sep);
                paths = paths.concat(subkeys.map(function (subkey) {
                    return key + sep + subkey;
                }));
            }
        }
        return paths;
    },
    map({ from, sources, to, target, triggerIf = true }) {
        if (from && triggerIf) {
            let toNamespae = to;
            let mappings = from
                .map(
                    fromNamespace => sources.map(
                        source => ({
                            [fromNamespace + "/" + source]: toNamespae + "/" + target
                        })
                    )
                )
                .flat()
                .reduce((i, j) => ({ ...i, ...j }), {});
            return mappings;
        } else {
            return null;
        }
    },
    zipMaps(args) {
        let maps = args.map(arg => this.map(arg));
        let result = {}
        for (let map of maps) {
            if (map) {
                for (let [source, target] of Object.entries(map)) {
                    if (!(source in result)) {
                        result[source] = []
                    }
                    result[source].push(target);
                }
            }
        }
        return result;
    },
    // formatting
    toSnakeCase(path) {
        return path
            .replaceAll("$", "")  // remove bound variable symbol $
            .replaceAll("/", "_") // replace path seperator / with _
            .replaceAll(/[A-Z]/g, // replace camelCase with snake_case
                letter => `_${letter.toLowerCase()}`
            )
    },
    toCamelCase(path) {
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
    },
    type(path) {
        if (path.includes('$room')) return 'room';
        if (path.includes('$endpoint')) return 'endpoint';
        if (path.includes('$')) return 'boundVariable';
        //else
        return 'localVariable';
    }
}