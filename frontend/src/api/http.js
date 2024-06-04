import axios from 'axios'
import { api } from './client.js'

// Create the URL

// LOAD ENV VARS
const mode = import.meta.env.MASCOPE_PUBLIC_MODE
const host = location.hostname
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT

// production api server is routed to api_port via nginx reverse proxy
let url = mode === 'production' ? `http://${host}` : `http://${host}:${api_port}`

const getSessionId = () => {
  // get session id for emitting sio finished events
  const sid = api.socket.id
  return sid
}

const logRequest = (request) => {
  console.log(`[http] Starting request to: ${request.method.toUpperCase()} ${request.url}`)
  return request
}

const logResponse = (response) => {
  let logMessage = `[http] Response: ${response.status} ${
    response.statusText
  } from ${response.config.method.toUpperCase()} ${response.config.url}`
  // Get process_id from headers
  if (response.headers['process-id']) {
    logMessage += ` | Process-ID: ${response.headers['process-id']}`
  }
  // Append the message if available
  if (response.data && response.data.message) {
    logMessage += ` | Message: ${response.data.message}`
  }

  console.log(logMessage)

  // Log the message-logs if available
  if (response.data && response.data['message-logs']) {
    console.log(`[http] Message-Logs:`, response.data['message-logs'])
  }

  return response
}

const handleError = (error) => {
  if (error.response) {
    console.log(`[http] Response Error: ${error.response.status} ${error.response.statusText}`)
  } else {
    console.log(`[http] Request Error: ${error.message}`)
  }
  return Promise.reject(error)
}

const workspacesBaseUrl = '/workspaces'
const batchesBaseUrl = '/sample_batches'
const samplesBaseUrl = '/samples'
const filesBaseUrl = '/sample_files'
const itemsBaseUrl = '/sample_items'
const calibrationBaseUrl = '/calibration'
const matchBaseUrl = '/match'
const matchesBaseUrl = '/matches'
const matchRatingsBaseUrl = '/match_ratings'
const targetCollectionsBaseUrl = '/target_collections'
const targetCollectionsInSampleBatchBaseUrl = '/target_collections_in_sample_batch'
const targetCompoundsBaseUrl = '/target_compounds'
const targetCompoundsInTargetCollectionBaseUrl = '/target_compound_in_target_collections'
const targetIonsBaseUrl = '/target_ions'
const ionizationMechanismsBaseUrl = '/ionization_mechanisms'
const targetIsotopesBaseUrl = '/target_isotopes'
const matchInterferencesBaseUrl = '/match_interferences'
const instrumentFunctionsBaseUrl = '/instrument_functions'
const attributeTemplatesBaseUrl = '/attribute_templates'
const visualizationBaseUrl = '/visualization'

export function createHttpClient() {
  const client = axios.create({
    baseURL: `${url}/api`,
    timeout: 20000
  })

  // Request interceptor to add X-SID header to every request, 'X-' prefix is a convention for custom headers
  client.interceptors.request.use(
    (config) => {
      const sid = getSessionId()
      if (sid) {
        config.headers['X-SID'] = sid
      }
      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )
  // Interceptor to log requests and responses
  client.interceptors.request.use(logRequest)
  client.interceptors.response.use(logResponse, handleError)

  return {
    ...client,
    // Workspaces
    getAllWorkspaces: async (params = {}) => {
      try {
        return await client.get(workspacesBaseUrl, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all workspaces: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getWorkspace: async ({ workspaceId }) => {
      try {
        return await client.get(`${workspacesBaseUrl}/${workspaceId}`)
      } catch (error) {
        const userErrorMessage = error?.response?.data?.error || `Failed to get workspace: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    createWorkspace: async (newWorkspace) => {
      try {
        return await client.post(workspacesBaseUrl, newWorkspace)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create workspace '${newWorkspace.workspace_name}': ${error}`
        throw new Error(userErrorMessage)
      }
    },
    deleteWorkspace: async (workspace) => {
      try {
        return await client.delete(`${workspacesBaseUrl}/${workspace.workspace_id}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete workspace '${workspace.workspace_name}': ${error}`
        throw new Error(userErrorMessage)
      }
    },
    updateWorkspace: async ({ workspaceId, body }) => {
      try {
        return await client.patch(`${workspacesBaseUrl}/${workspaceId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update workspace '${body.workspace_name}': ${error}`
        throw new Error(userErrorMessage)
      }
    },
    // Sample batches
    getAllBatches: async (params = {}) => {
      try {
        return await client.get(batchesBaseUrl, { params })
      } catch (error) {
        console.error('Failed to get all sample batches: ', error)
      }
    },
    getBatch: async ({ batchId }) => {
      try {
        return await client.get(`${batchesBaseUrl}/${batchId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get sample batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getBatchTargets: async ({ batchId, body }) => {
      try {
        return await client.post(`${batchesBaseUrl}/${batchId}/targets`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get batch targets data: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    createBatch: async (newBatch) => {
      try {
        return await client.post(batchesBaseUrl, newBatch)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create sample batch "${newBatch.sample_batch_name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    deleteBatch: async ({ sample_batch_id, sample_batch_name }) => {
      try {
        return await client.delete(`${batchesBaseUrl}/${sample_batch_id}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete sample batch "${sample_batch_name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    updateBatch: async ({ batchId, body }) => {
      try {
        return await client.patch(`${batchesBaseUrl}/${batchId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update sample batch "${body.sample_batch_name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    importSamplesToBatch: async ({ batch, body }) => {
      try {
        return await client.post(`${batchesBaseUrl}/${batch.sample_batch_id}/import`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to import samples: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    copySampleBatch: async ({ batchId, body }) => {
      try {
        return await client.post(`${batchesBaseUrl}/${batchId}/copy`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to copy sample batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    recalibrateSampleBatch: async ({ batchId, body }) => {
      try {
        return await client.post(`${calibrationBaseUrl}/mz_calibrate/batch/${batchId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to calibrate sample batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    batchExportPeakData: async ({ sample_batch_id }) => {
      try {
        return await client.get(`${batchesBaseUrl}/${sample_batch_id}/export_peaks`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to export sample batch peaks: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    // Samples
    getAllSamples: async (body) => {
      try {
        return await client.post(samplesBaseUrl, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get batch samples data: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getSample: async ({ sampleId, body }) => {
      try {
        return await client.post(`${samplesBaseUrl}/${sampleId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get the sample data: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getSampleIonMatches: async ({ sampleId, body }) => {
      try {
        return await client.post(`${samplesBaseUrl}/${sampleId}/ion_matches`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get sample ion match data: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getBatchMatchFilter: async (batchId) => {
      try {
        return await client.get(`${samplesBaseUrl}/batch_match_filter/${batchId}`)
      } catch (error) {
        console.error('Failed to initialize batch match filter: ', error)
      }
    },

    getSampleMatchFilter: async (sampleItemId, body) => {
      try {
        return await client.post(`${samplesBaseUrl}/${sampleItemId}/sample_match_filter`, body)
      } catch (error) {
        console.error('Failed to initialize sample match filter: ', error)
      }
    },

    // Sample Files
    getAllSampleFiles: async (params = {}) => {
      try {
        return await client.get(filesBaseUrl, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all sample files: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getRecentSampleFiles: async (params = {}) => {
      try {
        return await client.get(`${filesBaseUrl}/recent`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get recent acquisitions: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getSampleFileById: async (sample_file_id) => {
      try {
        return await client.get(`${filesBaseUrl}/${sample_file_id}`)
      } catch (error) {
        console.error('Failed to get sample file: ', error)
      }
    },
    createSampleFile: async (newSampleFile) => {
      try {
        return await client.post(filesBaseUrl, newSampleFile)
      } catch (error) {
        console.error('Failed to create sample file: ', error)
      }
    },
    deleteSampleFile: async (sample_file_id) => {
      try {
        return await client.delete(`${filesBaseUrl}/${sample_file_id}`)
      } catch (error) {
        console.error('Failed to delete sample file: ', error)
      }
    },
    updateSampleFile: async (sample_file_id, updatedSampleFile) => {
      try {
        return await client.patch(`${filesBaseUrl}/${sample_file_id}`, updatedSampleFile)
      } catch (error) {
        console.error('Failed to update sample file: ', error)
      }
    },
    getSampleSpectrum: async ({ sample_file_id }) => {
      try {
        return await client.get(`${filesBaseUrl}/${sample_file_id}/spectrum`)
      } catch (error) {
        console.error('Failed to get sample spectrum: ', error)
      }
    },

    // Sample Items
    getAllSampleItems: async (params = {}) => {
      try {
        return await client.get(itemsBaseUrl, { params })
      } catch (error) {
        console.error('Failed to get all sample items: ', error)
      }
    },
    getSampleItemById: async (sample_item_id) => {
      try {
        return await client.get(`${itemsBaseUrl}/${sample_item_id}`)
      } catch (error) {
        console.error('Failed to get sample item: ', error)
      }
    },

    createSampleItem: async (sample) => {
      try {
        return await client.post(itemsBaseUrl, sample)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create sample item ${sample.sample_item_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    processSampleItem: async ({ sample, alarms, params }) => {
      try {
        return await client.post(`${itemsBaseUrl}/process`, {
          sample_item: sample,
          mz_calibration_params: params,
          alarms_list: alarms
        })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to process sample item ${sample.sample_item_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    updateSampleItem: async ({ sampleId, body }) => {
      try {
        return await client.patch(`${itemsBaseUrl}/${sampleId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update sample item ${body.sample_item_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    deleteSampleItem: async ({ sampleId }) => {
      try {
        return await client.delete(`${itemsBaseUrl}/${sampleId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to delete sample item: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    copySampleItem: async ({ sampleId, body }) => {
      try {
        return await client.post(`${itemsBaseUrl}/${sampleId}/copy`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to copy sample item: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Calibration
    getMzCalibration: async (params) => {
      try {
        return await client.get(`${calibrationBaseUrl}/mz_calibration`, {
          params
        })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get sample mz calibration: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    calibrationMzFit: async ({ sampleId, sampleName, body }) => {
      try {
        const config = {
          params: {
            sample_item_id: sampleId
          }
        }
        return await client.post(`${calibrationBaseUrl}/mz_fit`, body, config)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to mz fit sample '${sampleName}': ${error}`
        throw new Error(userErrorMessage)
      }
    },

    calibrationMzApply: async ({ fit, filename }) => {
      try {
        const config = {
          params: {
            filename
          }
        }
        const body = { fit }

        return await client.post(`${calibrationBaseUrl}/mz_apply`, body, config)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to apply mz calibration for '${filename}': ${error}`
        throw new Error(userErrorMessage)
      }
    },

    calibrationMzCalibrateSample: async ({ sampleId, sampleName, body }) => {
      try {
        return await client.post(`${calibrationBaseUrl}/mz_calibrate/sample/${sampleId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to m/z calibrate sample '${sampleName}': ${error}`
        throw new Error(userErrorMessage)
      }
    },

    calibrationMzCalibrateBatch: async ({ batch, body }) => {
      try {
        return await client.post(
          `${calibrationBaseUrl}/mz_calibrate/batch/${batch.sample_batch_id}`,
          body
        )
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to m/z calibrate sample batch '${batch.sample_batch_name}': ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Matches
    getAllMatches: async (params = {}) => {
      try {
        return await client.get(`${matchesBaseUrl}`, { params })
      } catch (error) {
        const userErrorMessage = error?.response?.data?.error || `Failed to get matches: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getMatchById: async (matchId) => {
      try {
        return await client.get(`${matchesBaseUrl}/${matchId}`)
      } catch (error) {
        console.error('Failed to get match by id: ', error)
      }
    },

    // Match
    rematchBatch: async ({ batchId, body = {} }) => {
      try {
        return await client.post(`${matchBaseUrl}/batch/${batchId}/rematch`, body)
      } catch (error) {
        const userErrorMessage = error?.response?.data?.error || `Failed to rematch batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    matchSampleCompute: async ({ sampleId, body = {} }) => {
      try {
        return await client.post(`${matchBaseUrl}/sample/${sampleId}/compute`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to compute mathes for sample: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    rematchSample: async ({ sampleId, body = {} }) => {
      try {
        return await client.post(`${matchBaseUrl}/sample/${sampleId}/rematch`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to rematch sample: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Match Ratings
    submitMatchRating: async (newMatchRating) => {
      try {
        return await client.post(matchRatingsBaseUrl, newMatchRating)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to submit match rating: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Target collections
    getAllTargetCollections: async (params = {}) => {
      try {
        return await client.get(`${targetCollectionsBaseUrl}`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all target collections: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getTargetCollection: async (collectionId) => {
      try {
        return await client.get(`${targetCollectionsBaseUrl}/${collectionId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get target collection: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    createTargetCollection: async (newCollection) => {
      try {
        return await client.post(targetCollectionsBaseUrl, newCollection)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create target collection ${newCollection.target_collection_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    updateTargetCollection: async ({ collectionId, body }) => {
      try {
        return await client.patch(`${targetCollectionsBaseUrl}/${collectionId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update target collection ${body.target_collection_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    deleteTargetCollection: async ({ collectionId, collectionName, deleteOrphanCompounds }) => {
      try {
        return await client.delete(`${targetCollectionsBaseUrl}/${collectionId}`, {
          params: {
            delete_orphan_compounds: deleteOrphanCompounds
          }
        })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete target collection ${collectionName}: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Target Collections in Sample Batch
    getAllTargetCollectionsInSampleBatchByParams: async (params = {}) => {
      try {
        return await client.get(targetCollectionsInSampleBatchBaseUrl, {
          params
        })
      } catch (error) {
        console.error('Failed to get target collections in sample batch: ', error)
      }
    },

    // Target compounds
    getAllTargetCompounds: async (params = {}) => {
      try {
        return await client.get(`${targetCompoundsBaseUrl}`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all target compounds: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getTargetCompoundById: async (targetCompoundId) => {
      try {
        return await client.get(`${targetCompoundsBaseUrl}/${targetCompoundId}`)
      } catch (error) {
        console.error('Failed to get target compound by id: ', error)
      }
    },

    createTargetCompounds: async (targetCompounds) => {
      try {
        return await client.post(targetCompoundsBaseUrl, targetCompounds)
      } catch (error) {
        console.error('Failed to create target compounds: ', error)
      }
    },
    updateTargetCompounds: async (targetCompounds) => {
      try {
        return await client.patch(targetCompoundsBaseUrl, targetCompounds)
      } catch (error) {
        console.error('Failed to update target compounds: ', error)
      }
    },
    deleteTargetCompound: async (targetCompoundId) => {
      try {
        return await client.delete(`${targetCompoundsBaseUrl}/${targetCompoundId}`)
      } catch (error) {
        console.error('Failed to delete target compound: ', error)
      }
    },

    // Target compound in target collections
    getAllTargetCompoundsInTargetCollection: async (params = {}) => {
      try {
        return await client.get(`${targetCompoundsInTargetCollectionBaseUrl}`, {
          params
        })
      } catch (error) {
        console.error('Failed to get all target compound in target collections: ', error)
      }
    },

    // Target ions
    getAllTargetIons: async (params = {}) => {
      try {
        return await client.get(`${targetIonsBaseUrl}`, { params })
      } catch (error) {
        console.error('Failed to get all target ions: ', error)
      }
    },

    getTargetIon: async (targetIonId) => {
      try {
        return await client.get(`${targetIonsBaseUrl}/${targetIonId}`)
      } catch (error) {
        console.error('Failed to get target ion: ', error)
      }
    },
    updateTargetIon: async (data) => {
      try {
        return await client.patch(`${targetIonsBaseUrl}/${data.target_ion_id}`, data.body)
      } catch (error) {
        console.error(`Failed to update target ion ${data.target_ion_formula}`, error)
      }
    },
    saveTargetIonFilterParams: async (data) => {
      try {
        const response = await client.patch(`${targetIonsBaseUrl}/${data.target_ion_id}`, data.body)
        // TEMP the message forming should move to api route
        const successMessage = `Filtering parameters for '${data.target_ion_formula}' saved successfully!`
        response.data.message = successMessage
        return response
      } catch (error) {
        const userErrorMessage = `Failed to save filtering parameters: ${error?.response?.data?.error || error}. Please try again.`
        throw new Error(userErrorMessage)
      }
    },
    deleteTargetIonFilterParams: async (data) => {
      try {
        const response = await client.patch(`${targetIonsBaseUrl}/${data.target_ion_id}`, data.body)
        // TEMP the message forming should move to api route
        const successMessage = `Filtering parameters for '${data.body.delete_instrument_filters}' instrument were deleted successfully!`
        response.data.message = successMessage
        return response
      } catch (error) {
        const userErrorMessage = `Failed to delete filtering parameters: ${error?.response?.data?.error || error}. Please try again.`
        throw new Error(userErrorMessage)
      }
    },

    // Ionization mechanisms
    getAllIonizationMechanisms: async (params = {}) => {
      try {
        return await client.get(`${ionizationMechanismsBaseUrl}`, {
          params
        })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all ionization mechanisms: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getIonizationMechanismById: async (ionizationMechanismId) => {
      try {
        return await client.get(`${ionizationMechanismsBaseUrl}/${ionizationMechanismId}`)
      } catch (error) {
        console.error('Failed to get ionization mechanism by id: ', error)
      }
    },
    // Target isotopes
    getAllTargetIsotopes: async (params = {}) => {
      try {
        return await client.get(`${targetIsotopesBaseUrl}`, { params })
      } catch (error) {
        console.error('Failed to get all target isotopes: ', error)
      }
    },
    getTargetIsotopeById: async (isotopeId) => {
      try {
        return await client.get(`${targetIsotopesBaseUrl}/${isotopeId}`)
      } catch (error) {
        console.error('Failed to get target isotope by id: ', error)
      }
    },

    // Match interferences
    getAllMatchInterferences: async (params = {}) => {
      try {
        return await client.get(`${matchInterferencesBaseUrl}`, { params })
      } catch (error) {
        console.error('Failed to get all match interferences: ', error)
      }
    },
    getMatchInterferenceById: async (interferenceId) => {
      try {
        return await client.get(`${matchInterferencesBaseUrl}/${interferenceId}`)
      } catch (error) {
        console.error('Failed to get match interference by id: ', error)
      }
    },

    // Instrument functions
    getAllInstrumentFunctions: async (params = {}) => {
      try {
        return await client.get(`${instrumentFunctionsBaseUrl}`, {
          params
        })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all instrument functions: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getInstrumentFunction: async (params = {}) => {
      try {
        return await client.get(`${instrumentFunctionsBaseUrl}/`, {
          params
        })
      } catch (error) {
        console.error('Failed to get instrument function by id: ', error)
      }
    },

    // Attribute templates
    getAllAttributeTemplates: async (params = {}) => {
      try {
        return await client.get(`${attributeTemplatesBaseUrl}`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get attribute templates: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getAttributeTemplate: async (templateId) => {
      try {
        return await client.get(`${attributeTemplatesBaseUrl}/${templateId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to get attribute template with ID "${templateId}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    createAttributeTemplate: async (newTemplate) => {
      try {
        return await client.post(attributeTemplatesBaseUrl, newTemplate)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create attribute template "${newTemplate.name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },

    updateAttributeTemplate: async ({ templateId, body }) => {
      try {
        return await client.patch(`${attributeTemplatesBaseUrl}/${templateId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update attribute template "${body.name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },

    deleteAttributeTemplate: async ({ templateId, templateName }) => {
      try {
        return await client.delete(`${attributeTemplatesBaseUrl}/${templateId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete attribute template "${templateName}: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Visualization
    getVisualizationIonFocus: async (params = {}) => {
      try {
        return await client.get(`${visualizationBaseUrl}/ion_focus`, {
          params
        })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to visualize ion '${params.target_ion_id}' focus for sample '${params.sample_item_id}': ${error}`
        throw new Error(userErrorMessage)
      }
    }
  }
}
