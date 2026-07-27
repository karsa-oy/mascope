import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { Decoder } from 'socket.io-parser'

import { initSocket } from '@/api/socket'

// A payload failing to decode client-side (invalid JSON, attachment overflow)
// makes socket.io close the connection with reason "parse error". These tests
// pin down the two defenses: the decoder must not cap binary attachments for
// our own backend, and a decode failure must not trigger the reconnect page
// reload (which historically looped: reload -> auto-fired request -> same bad
// payload -> parse error -> reload).

const { pushSpy, ioState } = vi.hoisted(() => ({
  pushSpy: vi.fn(),
  ioState: { lastOpts: null, socket: null }
}))

vi.mock('socket.io-client', () => ({
  io: (url, opts) => {
    ioState.lastOpts = opts
    return ioState.socket
  }
}))
vi.mock('@/stores', () => ({
  useApp: () => ({ ui: { notification: { push: pushSpy } } })
}))
vi.mock('@/lib/runtime.js', () => ({
  runtime: { mode: 'prod', meta: {} }
}))

function makeFakeSocket() {
  const handlers = new Map()
  const add = (event, fn) => {
    if (!handlers.has(event)) handlers.set(event, [])
    handlers.get(event).push(fn)
  }
  return {
    connected: true,
    on: add,
    once: add,
    onAny: () => {},
    emit: vi.fn(),
    io: { on: () => {} },
    fire(event, ...args) {
      for (const fn of handlers.get(event) ?? []) fn(...args)
    }
  }
}

describe('initSocket', () => {
  let socket
  let reloadSpy

  beforeEach(async () => {
    vi.clearAllMocks()
    ioState.socket = makeFakeSocket()
    reloadSpy = vi.spyOn(window.location, 'reload').mockImplementation(() => {})
    ;({ socket } = await initSocket())
  })

  afterEach(() => {
    reloadSpy.mockRestore()
  })

  it('configures a decoder without a practical attachment limit', () => {
    // 500 attachments: a binary event header a large ion focus payload produces
    const bigBinaryHeader = '5500-["visualization_signal_sum_spectrum"]'

    const CustomDecoder = ioState.lastOpts.parser.Decoder
    expect(() => new CustomDecoder().add(bigBinaryHeader)).not.toThrow()

    // the stock decoder rejects it, which is why the override exists
    expect(() => new Decoder().add(bigBinaryHeader)).toThrow(/too many attachments/)
  })

  it('reloads the page on reconnect after a network-level drop', () => {
    socket.fire('disconnect', 'transport close')
    socket.fire('connect')

    expect(reloadSpy).toHaveBeenCalledTimes(1)
  })

  it('skips the reload when the disconnect was a payload decode failure', () => {
    socket.addSubscription('user-1')
    socket.fire('disconnect', 'parse error')
    socket.fire('connect')

    expect(reloadSpy).not.toHaveBeenCalled()
    // the socket still recovers: rooms re-subscribed, reconnect reported
    expect(socket.emit).toHaveBeenCalledWith('subscribe', 'user-1')
    expect(pushSpy).toHaveBeenCalledWith(expect.objectContaining({ status: 'success' }))
  })

  it('reloads again on a later reconnect for a different reason', () => {
    socket.fire('disconnect', 'parse error')
    socket.fire('connect')
    socket.fire('disconnect', 'transport close')
    socket.fire('connect')

    expect(reloadSpy).toHaveBeenCalledTimes(1)
  })
})
