import { io } from "socket.io-client";

import initSqlJs from "sql.js";

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

    // open duckdb file served from backend
    const path = "http://localhost:8080/@fs/data/database"
    const file = `mascope.v${dbVersion}.db`
    const sqlPromise = initSqlJs({
        locateFile: file => `./node_modules/sql.js/dist/${file}`
      });
    const dataPromise = fetch(`${path}/${file}`).then(res => res.arrayBuffer());
    const [SQL, buf] = await Promise.all([sqlPromise, dataPromise])
    const dbcon = new SQL.Database(new Uint8Array(buf));

    apiLog('registered database URL', path);

    // helpers
    function tryJsonParse(value) {
        try {
            return JSON.parse(value);
        } catch {
            return value;
        }
    }

    async function asObject(resp) {
        if (!resp.length) return resp;
        let fields = resp[0].columns;
        let rows = resp[0].values;
        return rows.map(
            (row) => Object.fromEntries(
                fields.map((field, index) => [field, tryJsonParse(row[index])])
                )
            )
    }

    const emit = (ev, ...args) => socket.emit(ev, ...args);
    const query = (text) => asObject( dbcon.exec(text) );

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