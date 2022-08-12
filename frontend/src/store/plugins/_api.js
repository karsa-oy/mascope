import { io } from "socket.io-client";
import Vue from 'vue';

// duckdb imports
import * as duckdb from '@duckdb/duckdb-wasm';
import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_next from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

const HANDLER_PREFIX = 'on'


export default async function api(store) {

    // LOAD ENV VARS

    const protocol = import.meta.env.MASCOPE_PUBLIC_API_PROTOCOL;
    const host = import.meta.env.MASCOPE_PUBLIC_API_HOST;
    const port = import.meta.env.MASCOPE_PUBLIC_API_PORT;
    const dbVersion = import.meta.env.MASCOPE_PUBLIC_DB_VERSION;

    // INIT SOCKET

    // create the socket in the `/api` namespace
    const url = `${protocol}://${host}:${port}/api`;
    const socket = io(url);
    Vue.prototype.$socket = socket;

    apiLog('initialized socket', socket);

    // find event handlers in store actions
    let handlers = Object.keys(store._actions)
        .filter(path => getAction(path).startsWith(HANDLER_PREFIX))
        .map(path => ({ [getEvent(path)]: path }))
        .reduce((prev, curr) => ({ ...prev, ...curr }), {});

    // react to events using handlers if they exist
    socket.onAny((event, ...args) => {
        apiLog(`${event} event detected`, args)
        if (event in handlers) {
            store.dispatch(handlers[event], args);
        }

    });

    apiLog('registered event handlers', handlers);

    // INIT DATABASE

    // select a bundle based on browser checks
    const bundle = await duckdb.selectBundle({
        mvp: {
            mainModule: duckdb_wasm,
            mainWorker: mvp_worker,
        },
        eh: {
            mainModule: duckdb_wasm_next,
            mainWorker: eh_worker
        },
    });

    // init async duckdb-wasm
    const worker = new Worker(bundle.mainWorker);
    const logger = new duckdb.ConsoleLogger();
    const db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

    apiLog('instantiated database', db);

    // open duckdb file served from backend
    const basePath = "http://localhost:8080/@fs/data/database"
    const path = `${basePath}/mascope.v${dbVersion}.duckdb`
    await db.registerFileURL(path);

    apiLog('registered database URL', path);

    await db.open({ path });

    apiLog('opened database');

    // establish connection
    const dbcon = await db.connect();
    Vue.prototype.$dbcon = dbcon;

    apiLog('initialized database connection', dbcon)

    // CREATE STORE MODULE

    store.registerModule('api', {
        namespaced: true,
        state: {
            socket,
            dbcon
        },
    })

    apiLog('registered api store module');

    // LOAD INITIAL DATA

    store.dispatch('app/load')

    apiLog('loaded root data');
}


// logging 

let apiLogPrefix = '[API]';

function apiLog(...args) {
    console.log(apiLogPrefix, ...args)
}

function apiLogGroup(...args) {
    console.groupCollapsed(apiLogPrefix, ...args)
}

function apiLogGroupEnd() {
    console.groupEnd();
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
