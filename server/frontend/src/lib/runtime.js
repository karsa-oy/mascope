function initRuntime() {
  // parse runtime serialized in env var
  const runtime = JSON.parse(import.meta.env.MASCOPE_RUNTIME)
  // build the full api base path
  const host = location.hostname
  const mode = import.meta.env.MODE
  // In a production build the app is served behind nginx (which proxies /api/),
  // so use the page's actual origin -- this works whether served over HTTPS
  // (e.g. https://mascope.app) or plain HTTP (e.g. http://localhost:8080),
  // instead of assuming HTTPS.
  const api_path =
    mode === 'production' ? location.origin : `http://${host}:${runtime.meta.api_port}`
  runtime['api_path'] = api_path

  return runtime
}

export const runtime = initRuntime()

console.log('⚛️ [runtime] initialized', runtime ?? import.meta.env.MASCOPE_RUNTIME)
