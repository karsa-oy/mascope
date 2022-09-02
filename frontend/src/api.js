import { io } from "socket.io-client";

import initSqlJs from "sql.js";

// LOAD ENV VARS

const dbVersion = import.meta.env.MASCOPE_PUBLIC_DB_VERSION;
const protocol = import.meta.env.MASCOPE_PUBLIC_API_PROTOCOL;
const host = import.meta.env.MASCOPE_PUBLIC_API_HOST;
const port = import.meta.env.MASCOPE_PUBLIC_API_PORT;


export const api = await initApi();


async function initDb() {
    // INIT DATABASE

    // open db file served from backend
    const path = "http://localhost:8080/@fs/data/database"
    const file = `mascope.v${dbVersion}.db`
    const sqlPromise = initSqlJs({
        locateFile: file => `./node_modules/sql.js/dist/${file}`
      });
    const dataPromise = fetch(`${path}/${file}`).then(res => res.arrayBuffer());
    const [SQL, buf] = await Promise.all([sqlPromise, dataPromise])
    const dbcon = new SQL.Database(new Uint8Array(buf));

    apiLog('registered database URL', path);
    const query = (text) => asObject( dbcon.exec(text) );
    return [dbcon, query];
}

async function initSocket() {
    // INIT SOCKET

    // create the socket in `/` namespace
    const url = `${protocol}://${host}:${port}`;
    const socket = io(url);
    apiLog('initialized socket', socket);
    const emit = (ev, ...args) => socket.emit(ev, ...args);
    return [socket, emit];
}

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

async function initApi() {
    const [socket, emit] = await initSocket();
    const [dbcon, query] = await initDb();

    const api = {
        socket,
        dbcon,
        emit,
        query,
        initDb
    };

    return api;
}

// logging 

export function apiLog(...args) {
    console.log('[API]', ...args)
}