import { api } from './client.js'

const HANDLER_PREFIX = 'on'

export async function apiPlugin({ store }) {
  // REGISTER EVENT HANDLERS

  let handlers = Object.keys(store)
    .filter(
      (path) => getAction(path).startsWith(HANDLER_PREFIX) && getAction(path) !== HANDLER_PREFIX
    )
    .map((path) => ({ [getEvent(path)]: path }))
    .reduce((prev, curr) => ({ ...prev, ...curr }), {})
  // react to events using handlers if they exist
  api.socket.onAny((event, ...args) => {
    if (event in handlers) {
      api.log(`${store.$id} received event "${event}"`, ...args)
      const handler = handlers[event]
      store[handler](...args)
    }
  })

  api.log(`${store.$id} registered event handlers`, handlers)
}

// path parsing

function getAction(path) {
  const pathItems = path.split('/')
  const action = pathItems[pathItems.length - 1]
  return action
}

function getEvent(path) {
  const action = getAction(path)
  const actionWithoutPrefix = action.replace(HANDLER_PREFIX, '')
  return toSnakeCase(actionWithoutPrefix)
}

// case conversion

function toSnakeCase(string) {
  let s = string[0].toLowerCase() + string.slice(1)
  return s
    .replaceAll('/', '_') // replace path seperator / with _
    .replaceAll(
      /[A-Z]/g, // replace camelCase with snake_case
      (letter) => `_${letter.toLowerCase()}`
    )
}
