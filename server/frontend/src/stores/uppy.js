import { defineStore } from 'pinia'
import { ref } from 'vue'

import Uppy from '@uppy/core'
import Tus from '@uppy/tus'

import { useIonizationMode } from './data/modules/ionization'
import { useUi } from './ui'

import { api } from '@/api'
import { runtime } from '@/lib/runtime.js'
import { genId, instrumentType } from '@/lib/utils'

// TODO_configuration Default sample file upload params
const FILE_UPLOAD_EXTENSIONS = ['.h5', '.raw']
const FILE_UPLOAD_SIZE_LIMIT = 2.5 * 1024 * 1024 * 1024 // 2.5 GB

function validateFile(file) {
  const validInstrument = validateInstrument(file)
  const validIonization = validateIonization(file)
  return validInstrument && validIonization
}

function validateInstrument(file) {
  // parse filename
  const prefix = file.name.split('_')[0]
  const prefixType = instrumentType(prefix)
  const ext = file.name.split('.').slice(-1)[0].toLowerCase()
  // check filename validity
  if (ext === 'h5' && prefixType !== 'tof') {
    return false
  } else if (ext === 'raw' && prefixType !== 'orbi') {
    return false
  } else {
    return true
  }
}

function validateIonization(file) {
  const ionization = useIonizationMode().list.some((i) =>
    file.name.includes(i.ionization_mode_token)
  )
  if (!ionization) return false
  return true
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
    endpoint: `${runtime.api_path}/api/sample/files/upload/tus`,
    // settings
    retryDelays: [0, 3000, 5000, 10000, 20000],
    chunkSize: 5 * 1024 * 1024, // 5 MiB, small chunks seem the most reliable
    withCredentials: true,
    removeFingerprintOnSuccess: true,
    limit: 1, // Upload files sequentially, one by one
    onShouldRetry: (err, retryAttempt, options, next) => {
      console.log('[uppy] Upload error:', err)
      const status = err?.originalResponse?.getStatus()
      if (status === undefined || status === 0 || (status >= 500 && status < 600)) {
        // Proceed to retry unless the error is client-side
        return true
      }
      return next(err)
    },
    onBeforeRequest: (req) => {
      req.setHeader('X-SID', api.socket.id)
    }
  })
  // Register event handlers to track upload progress
  let process_id

  uppy.on('upload', () => {
    process_id = genId(8)
  })
  uppy.on('progress', (progress) => {
    if (progress === 100) return
    ui.notification.push({
      type: 'sample_file_upload',
      process_id,
      status: 'pending',
      message: `Uploaded ${progress}% of sample files`,
      progress
    })
  })

  uppy.on('complete', (result) => {
    // Handle successful uploads
    if (result.successful.length > 0) {
      const message =
        result.successful.length === 1
          ? `Uploaded ${result.successful[0].name} successfully!`
          : `Uploaded ${result.successful.length} sample files successfully!`

      ui.notification.push({
        type: 'sample_file_upload',
        process_id,
        status: 'success',
        message,
        progress: 100
      })
    }

    // Handle failed uploads
    if (result.failed.length > 0) {
      result.failed.forEach((file) => {
        // Extract api error message from TUS error string
        const errorMessage = (() => {
          try {
            const jsonStr = file.error?.split('response text: ')[1]?.split(', request id:')[0]
            return jsonStr ? JSON.parse(jsonStr).error : 'Upload failed'
          } catch {
            return 'Upload failed'
          }
        })()

        ui.notification.push({
          type: 'sample_file_upload',
          process_id,
          status: 'error',
          message: `${file.name}: ${errorMessage}`
        })

        console.error(`Upload failed for ${file.name}:`, file.error)
      })
    }
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
