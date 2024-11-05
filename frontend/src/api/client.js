import { createHttpClient } from './http.js'

import { runtime } from '@/lib/runtime.js'
import { strToSnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'
import { genId } from '@/lib/utils'

import { initSocket } from './socket.js'

export const api = await initApi()

async function initApi() {
  const socket = await initSocket()
  const http = createHttpClient(location.hostname, runtime.meta.api_port)

  // Catch errors, show error norification and return response from api
  async function apiResponse({ method, body = {} }) {
    const app = useApp()
    try {
      return await http[method](body)
    } catch (error) {
      console.error(`Failed to ${method}:`, error)
      app.ui.notification.push({
        type: strToSnakeCase(method),
        status: 'error',
        message: error.message
      })
    }
  }

  const log = (...args) => console.log('[api]', ...args)

  const request = {
    // method to write the data to api (http_methods: POST, success_status: 201)
    create: async ({ method, body = {} }) => {
      const app = useApp()
      const { data, status } = await apiResponse({ method, body })
      if (status === 201) {
        app.ui.notification.push({
          type: strToSnakeCase(method),
          status: 'success',
          message: data.message,
          data: {
            request: {
              body,
              method
            },
            response: {
              data,
              status
            }
          }
        })
        return data
      }
    },

    /**
     * Uploads multiple files to the specified API endpoint and tracks their progress.
     * This method uses `Promise.all` to handle parallel file uploads and updates the UI
     * with progress notifications for each file.
     *
     * - A unique `process_id` is generated for each file to track its upload progress individually.
     * - A `mainProcessId` is generated to group the overall progress and status of the upload process.
     * - Each file's upload progress is tracked and updated in the UI using a callback.
     * - If an upload fails, an error notification is pushed to the UI.
     * - A summary notification is emitted based on the success and error counts after all uploads complete.
     *
     * @param {Object} params - The upload parameters.
     * @param {string} params.method - The HTTP method used for uploading files.
     * @param {Array<File>} params.files - The array of files to be uploaded.
     */
    upload: async ({ method, files }) => {
      const app = useApp()
      const mainProcessId = genId(8) // Generate a unique ID for the overall upload process
      let successes = 0 // Counter to track the number of successful uploads
      let errors = 0 // Counter to track the number of failed uploads

      // Use Promise.all to handle multiple file uploads in parallel
      await Promise.all(
        files.map(async (file) => {
          const process_id = genId(8) // Generate a unique ID for each file upload
          try {
            // Make the upload request with progress tracking
            const response = await http[method]({
              file, // The file being uploaded
              progressCallback: (progressEvent) => {
                const percentCompleted = progressEvent.progress * 100 // Calculate progress percentage

                // Update the progress for the current file
                app.ui.notification.push({
                  type: 'sample_file_upload',
                  process_id,
                  parent_id: mainProcessId,
                  status: 'pending',
                  message: `${file.name} - ${percentCompleted.toFixed(2)}% uploaded`,
                  progress: percentCompleted
                })
              }
            })

            // If the upload is successful, send a success notification for this file
            if (response?.status === 201) {
              successes += 1
              app.ui.notification.push({
                type: 'sample_file_upload',
                process_id,
                parent_id: mainProcessId,
                status: 'success',
                message: `File ${file.name} uploaded successfully!`,
                progress: 100
              })
            }
          } catch (error) {
            // Handle upload errors for this specific file
            errors += 1
            const errorMessage = `Failed to upload file ${file.name}: ${error.message}`
            app.ui.notification.push({
              type: 'sample_file_upload',
              process_id,
              parent_id: mainProcessId,
              status: 'error',
              message: errorMessage
            })

            console.error(`Failed to ${method} ${file.name}:`, error)
          }
        })
      )

      // Emit a summary notification based on the success and error counts
      if (successes > 0 && errors === 0) {
        // All uploads were successful
        const s = successes > 1 ? 's' : ''
        app.ui.notification.push({
          type: 'sample_file_upload',
          status: 'success',
          process_id: mainProcessId,
          progress: 100,
          message: `Successfully uploaded ${successes} file${s}`
        })
      } else if (successes > 0 && errors > 0) {
        // Some uploads were successful, some failed
        const s = successes > 1 ? 's' : ''
        app.ui.notification.push({
          type: 'sample_file_upload',
          status: 'warning',
          process_id: mainProcessId,
          progress: 100,
          message: `Successfully uploaded ${successes} file${s}, but failed to upload ${errors} file${errors > 1 ? 's' : ''}`
        })
      } else if (errors > 0) {
        // All uploads failed
        app.ui.notification.push({
          type: 'sample_file_upload',
          status: 'error',
          process_id: mainProcessId,
          progress: 100,
          message: `Failed to upload all ${errors} file${errors > 1 ? 's' : ''}`
        })
      }
    },

    // method to get the data from api (http_methods: GET,POST, success_status: 200)
    read: async ({ method, body = {} }) => {
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        return data
      }
    },
    // method to update the data in api (http_methods: PATCH, success_status: 200)
    update: async ({ method, body = {} }) => {
      const app = useApp()
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        app.ui.notification.push({
          type: strToSnakeCase(method),
          status: 'success',
          message: data.message,
          data: {
            request: {
              body,
              method
            },
            response: {
              data,
              status
            }
          }
        })
      }
    },
    // method to delete the data from api (http_methods: DELETE, success_status: 200)
    delete: async ({ method, body = {} }) => {
      const app = useApp()
      const { data, status } = await apiResponse({ method, body })
      if (status === 200) {
        app.ui.notification.push({
          type: strToSnakeCase(method),
          status: 'success',
          message: data.message,
          data: {
            request: {
              body,
              method
            },
            response: {
              data,
              status
            }
          }
        })
      }
    },
    // method to start the long running process in api (http_methods: GET, POST, success_status: 202, data is returned in sio user_notifications)
    process: async ({ method, body = {} }) => {
      const { data, status } = await apiResponse({ method, body })
      if (status === 202) {
        log('Progress notification', data)
      }
    }
  }

  return {
    client: http.client,
    http,
    socket,
    request,
    log
  }
}
