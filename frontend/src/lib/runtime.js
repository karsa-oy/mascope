export const runtime = JSON.parse(import.meta.env.MASCOPE_RUNTIME)

console.log('RUNTIME', runtime ?? import.meta.env.MASCOPE_RUNTIME)
