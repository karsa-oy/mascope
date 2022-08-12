import { io } from "socket.io-client";

// duckdb imports
import * as duckdb from '@duckdb/duckdb-wasm';
import duckdb_wasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvp_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import duckdb_wasm_next from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import eh_worker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

export const api = await initApi();

async function initApi() {
    const handlerPrefix = 'on';

    // LOAD ENV VARS

    const protocol = import.meta.env.MASCOPE_PUBLIC_API_PROTOCOL;
    const host = import.meta.env.MASCOPE_PUBLIC_API_HOST;
    const port = import.meta.env.MASCOPE_PUBLIC_API_PORT;
    const dbVersion = import.meta.env.MASCOPE_PUBLIC_DB_VERSION;

    // INIT SOCKET

    // create the socket in the `/api` namespace
    const url = `${protocol}://${host}:${port}/api`;
    const socket = io(url);

    apiLog('initialized socket', socket);

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

    apiLog('initialized database connection', dbcon)

    // helpers
    const emit = (ev, ...args) => socket.emit(ev, ...args);
    const query = (text) => dbcon.query(text);

    const api = {
        socket,
        dbcon,
        emit,
        query
    };

    return api;
}

// logging 

export function apiLog(...args) {
    console.log('[API]', ...args)
}