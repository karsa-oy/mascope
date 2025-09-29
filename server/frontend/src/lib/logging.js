export const makeLogger = (config) => {
  const level =
    (func) =>
    (body, { icon, data } = {}) =>
      func(
        ...[`${icon ?? config.icon} [${config.prefix}] ${body}`, data].filter(
          (e) => e !== undefined
        )
      )
  return {
    log: level(console.log),
    warn: level(console.warn),
    error: level(console.error),
    dir: level(console.dir),
    debug: level(console.debug)
  }
}
