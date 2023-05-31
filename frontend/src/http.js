import axios from "axios";

const host = location.hostname;
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT;

export const http = axios.create({
  baseURL: `http://${host}:${api_port}/api`,
  timeout: 15000,
});
