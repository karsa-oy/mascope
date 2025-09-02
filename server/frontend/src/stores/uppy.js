import { defineStore } from 'pinia'

import Uppy from '@uppy/core'
import Tus from '@uppy/tus'

import { useUi } from './ui'

import { api } from '@/api'
import { runtime } from '@/lib/runtime.js'
import { genId } from '@/lib/utils'

export const useUppy = defineStore('app.uppy', () => {
  const ui = useUi()
  const uppy = new Uppy({
    restrictions: {
      allowedFileTypes: ['.h5', '.raw'],
      maxFileSize: 4e9, // 4GB
      maxNumberOfFiles: 1000
    }
  }).use(Tus, {
    endpoint: `${runtime.api_path}/api/sample/files/upload`,
    // settings
    retryDelays: [0, 3000, 5000, 10000, 20000],
    chunkSize: 1e8, // 100MB
    // auth
    headers: {
      'X-SID': api.socket.id
    },
    withCredentials: true,
    removeFingerprintOnSuccess: true,
    onShouldRetry: (err, retryAttempt, options) => {
      console.log('Error', err)
      console.log('Request', err.originalRequest)
      console.log('Response', err.originalResponse)
    }
  })

  let process_id

  uppy.on('upload', () => {
    console.log('upload')
    process_id = genId(8)
  })
  uppy.on('progress', (progress) => {
    ui.notification.push({
      type: 'sample_file_upload',
      process_id,
      status: 'pending',
      message: `Uploaded ${progress}% of sample files`,
      progress
    })
  })

  uppy.on('error', (error) => {
    ui.notification.push({
      type: 'sample_file_upload',
      process_id,
      status: 'error',
      message: 'Sample file upload(s) failed'
    })
    console.error(error.stack)
  })

  uppy.on('complete', (result) => {
    if (result.successful.length === 1) {
      ui.notification.push({
        type: 'sample_file_upload',
        process_id,
        status: 'success',
        message: `Uploaded ${result.successful[0].name} successfully!`,
        progress: 100
      })
    } else if (result.successful.length > 1) {
      ui.notification.push({
        type: 'sample_file_upload',
        process_id,
        status: 'success',
        message: `Uploaded ${result.successful.length} sample files successfully!`,
        progress: 100
      })
    }
    result.failed.forEach(({ name, error }) => {
      ui.notification.push({
        type: 'sample_file_upload',
        process_id,
        status: 'error',
        message: `Failed to upload file ${name}: ${error}`
      })
      console.error(`Sample file upload failed:`, error)
    })
  })

  function get() {
    return uppy
  }
  return { get }
})
