function initRuntime() {
  // parse runtime serialized in env var
  const runtime = JSON.parse(import.meta.env.MASCOPE_RUNTIME)
  // build the full api base path
  const host = location.hostname
  const mode = import.meta.env.MODE
  const api_path =
    mode === 'production' ? `https://${host}` : `http://${host}:${runtime.meta.api_port}`
  runtime['api_path'] = api_path

  return runtime
}

export const runtime = initRuntime()

console.log('[runtime] initialized', runtime ?? import.meta.env.MASCOPE_RUNTIME)
