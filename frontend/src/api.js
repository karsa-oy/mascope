import { io } from "socket.io-client";
import initSqlJs from "sql.js";
import { createHttpClient } from "./httpClient.js";

// LOAD ENV VARS
const mode = import.meta.env.MASCOPE_PUBLIC_MODE;
const dbVersion = import.meta.env.MASCOPE_PUBLIC_DB_VERSION;
const protocol = import.meta.env.MASCOPE_PUBLIC_PROTOCOL;
const host = location.hostname;
const port = import.meta.env.MASCOPE_PUBLIC_PORT;
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT;
const platform = import.meta.env.MASCOPE_PRIVATE_ENV;
var dbpath = import.meta.env.MASCOPE_PRIVATE_DATADIR;

//TODO: tmp solution - sql.db must be linked to the frontend root with the same name
dbpath = dbpath.split("\\").pop().split("/").pop();

export const api = await initApi();

async function initDb() {
  // INIT DATABASE
  // open db file served from backend
  let path = "";
  if (platform.includes("inux")) {
    path = `${dbpath}/database`; // works for linux
  } else {
    path = `http://${host}:${port}/@fs/${dbpath}/database`; // works for win (mac?)
  }

  const file = `mascope.v${dbVersion}.db`;
  const sqlPromise = initSqlJs({
    locateFile: (file) => `./node_modules/sql.js/dist/${file}`,
  });
  const dataPromise = fetch(`${path}/${file}`).then((res) => res.arrayBuffer());
  const [SQL, buf] = await Promise.all([sqlPromise, dataPromise]);
  const dbcon = new SQL.Database(new Uint8Array(buf));

  apiLog("registered database URL", path);
  const query = (text) => asObject(dbcon.exec(text));
  return [dbcon, query];
}

async function initSocket() {
  // INIT API SOCKET

  // create the socket in `/` namespace
  let url = `${protocol}://${host}:${api_port}`;
  if (mode === "production") {
    // production api server is routed to api_port via nginx reverse proxy
    url = `${protocol}://${host}`;
  }
  const socket = io(url);
  apiLog("initialized socket for", mode, ":", url, socket);
  const emit = (ev, ...args) => {
    apiLog(`emitting event "${ev}"`, ...args);
    socket.emit(ev, ...args);
  };
  return [socket, emit];
}

// helpers
function tryJsonParse(value) {
  if (!value) return value;
  // only try to parse objects and arrays
  if (!["[", "{"].includes(value[0])) return value;
  try {
    // valud JSON object or array
    return JSON.parse(value);
  } catch {
    // not valid JSON object nor array
    return value;
  }
}

async function asObject(resp) {
  if (!resp.length) return resp;
  let fields = resp[0].columns;
  let rows = resp[0].values;
  return rows.map((row) =>
    Object.fromEntries(
      fields.map((field, index) => [field, tryJsonParse(row[index])])
    )
  );
}

async function initApi() {
  const [socket, emit] = await initSocket();
  const [dbcon, query] = await initDb();
  const httpClient = createHttpClient(host, api_port);

  const api = {
    socket,
    dbcon,
    emit,
    query,
    initDb,
    httpClient,
  };

  return api;
}

// logging

export function apiLog(...args) {
  console.log("[API]", ...args);
}
