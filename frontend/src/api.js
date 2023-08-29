import { io } from "socket.io-client";
import { createHttpClient } from "./httpClient.js";

// LOAD ENV VARS
const mode = import.meta.env.MASCOPE_PUBLIC_MODE;
const protocol = import.meta.env.MASCOPE_PUBLIC_PROTOCOL;
const host = location.hostname;
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT;

export const api = await initApi();

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

async function initApi() {
  const [socket, emit] = await initSocket();
  const httpClient = createHttpClient(host, api_port);

  const api = {
    socket,
    emit,
    httpClient,
  };

  return api;
}

// logging

export function apiLog(...args) {
  console.log("[API]", ...args);
}
