import { defineStore } from 'pinia'
import { ref } from 'vue'

import Uppy from '@uppy/core'
import Tus from '@uppy/tus'

import { useUi } from './ui'

import { api } from '@/api'
import { runtime } from '@/lib/runtime.js'
import { genId, instrumentType } from '@/lib/utils'

// TODO_configuration Default sample file upload params
const FILE_UPLOAD_EXTENSIONS = ['.h5', '.raw']
const FILE_UPLOAD_SIZE_LIMIT = 2.5 * 1024 * 1024 * 1024 // 2.5 GB

function validateFile(file) {
  // parse filename
  const prefix = file.name.split('_')[0]
  const prefixType = instrumentType(prefix)
  const ext = file.name.split('.').slice(-1)[0].toLowerCase()
  // check filename validity
  if (ext == 'h5' && prefixType !== 'tof') {
    return false
  } else if (ext == 'raw' && prefixType !== 'orbi') {
    return false
  } else {
    return true
  }
}

export const useUppy = defineStore('app.uppy', () => {
  const ui = useUi()

  const invalidFiles = ref([])

  const uppy = new Uppy({
    restrictions: {
      allowedFileTypes: FILE_UPLOAD_EXTENSIONS,
      maxFileSize: FILE_UPLOAD_SIZE_LIMIT,
      maxNumberOfFiles: 1000
    },
    onBeforeFileAdded: (currentFile, files) => {
      let isValid = validateFile(currentFile)
      if (!isValid) {
        invalidFiles.value = [...invalidFiles.value, currentFile]
        return false
      }
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
  // Register event handlers to track upload progress
  let process_id

  uppy.on('upload', () => {
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
  // End event handlers

  function get() {
    // Return the Uppy instance. This is to not wrap it in a reactive ref
    return uppy
  }

  function clearInvalid() {
    invalidFiles.value = []
  }

  return { get, clearInvalid, invalidFiles }
})
