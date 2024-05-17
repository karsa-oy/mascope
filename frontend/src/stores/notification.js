import { reactive, watchEffect, computed, onBeforeUnmount } from 'vue'
import { defineStore } from 'pinia'

import { genId } from '@/lib/utils'

export const useNotification = defineStore('notification', () => {
  const state = reactive({
    latest: null,
    log: [],
    watchers: [],
    progress: []
  })

  async function onUserNotification(notification) {
    push(notification)
  }
  function push(notification) {
    const id = genId()
    state.latest = { id, ...notification }
    state.log.push(notification)
  }
  function on(trigger, callback) {
    const id = genId()
    const types = Array.isArray(trigger) ? trigger : [trigger]
    types.forEach((type) => {
      state.watchers.push({ id, type, callback })
    })
    const destructor = () =>
      onBeforeUnmount(() => {
        state.watchers = state.watchers.filter((watcher) => watcher.id !== id)
      })
    return destructor
  }

  const findRoot = (process_id) => {
    const process = state.progress.find((proc) => proc.process_id == process_id)
    if (process?.parent_id) {
      return findRoot(process_id?.parent_id)
    } else {
      return process_id
    }
  }

  on('*', ({ type, process_id, parent_id, status, progress, message }) => {
    const saved = state.progress.find((proc) => proc.process_id == process_id)
    if (!saved) {
      if (status == 'pending') {
        // find root process
        // TODO: move this to the backend
        const root_id = findRoot(process_id)
        // track new process
        state.progress.push({
          type,
          process_id,
          parent_id,
          root_id,
          message,
          progress
        })
      }
    } else {
      // update existing process
      saved.progress = progress
      if (status !== 'pending') {
        // cleanup completed processes
        state.progress = state.progress.filter((proc) => proc.process_id !== process_id)
        if (status == 'error') {
          // if a parent fails, clean up the child processes
          state.progress = state.progress.filter((proc) => proc.root_id !== process_id)
        }
      }
    }
  })

  watchEffect(() => {
    state.watchers.forEach(({ type, callback }) => {
      if (state.latest?.id && (type == state.latest.type || type == '*')) {
        callback(state.latest)
      }
    })
  })

  return {
    // api
    on,
    push,
    latest: computed(() => state.latest),
    log: computed(() => state.log),
    progress: computed(() => state.progress),
    // listeners
    onUserNotification
  }
})
