import axios from 'axios'
import { api } from './client.js'

import { config } from '@/lib/config.js'

// Create the URL

// LOAD ENV VARS
const host = location.hostname
const mode = import.meta.env.MODE

// production api server is routed to api_port via nginx reverse proxy
let url = mode === 'production' ? `http://${host}` : `http://${host}:${config.server.port}`

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
    client,
    // Workspaces
    getAllWorkspaces: async (params = {}) => {
      try {
        return await client.get('/workspaces', { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all workspaces: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getWorkspace: async ({ workspaceId }) => {
      try {
        return await client.get(`/workspaces/${workspaceId}`)
      } catch (error) {
        const userErrorMessage = error?.response?.data?.error || `Failed to get workspace: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    createWorkspace: async (newWorkspace) => {
      try {
        return await client.post('/workspaces', newWorkspace)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create workspace '${newWorkspace.workspace_name}': ${error}`
        throw new Error(userErrorMessage)
      }
    },
    deleteWorkspace: async (workspace) => {
      try {
        return await client.delete(`/workspaces/${workspace.workspace_id}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete workspace '${workspace.workspace_name}': ${error}`
        throw new Error(userErrorMessage)
      }
    },
    updateWorkspace: async ({ workspaceId, body }) => {
      try {
        return await client.patch(`/workspaces/${workspaceId}`, body)
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
        return await client.get('/sample/batches', { params })
      } catch (error) {
        console.error('Failed to get all sample batches: ', error)
      }
    },
    getBatch: async ({ batchId }) => {
      try {
        return await client.get(`/sample/batches/${batchId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get sample batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getBatchTargets: async ({ batchId, body }) => {
      try {
        return await client.post(`/sample/batches/${batchId}/targets`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get batch targets data: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    createBatch: async (newBatch) => {
      try {
        return await client.post('/sample/batches', newBatch)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create sample batch "${newBatch.sample_batch_name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    deleteBatch: async ({ sample_batch_id, sample_batch_name }) => {
      try {
        return await client.delete(`/sample/batches/${sample_batch_id}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete sample batch "${sample_batch_name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    updateBatch: async ({ batchId, body }) => {
      try {
        return await client.patch(`/sample/batches/${batchId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update sample batch "${body.sample_batch_name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    importSamplesToBatch: async ({ batch, body }) => {
      try {
        return await client.post(`/sample/batches/${batch.sample_batch_id}/import`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to import samples: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    copySampleBatch: async ({ batchId, body }) => {
      try {
        return await client.post(`/sample/batches/${batchId}/copy`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to copy sample batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    recalibrateSampleBatch: async ({ batchId, body }) => {
      try {
        return await client.post(`/calibration/mz_calibrate/batch/${batchId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to calibrate sample batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getBatchAndAggregatedMatches: async ({ sample_batch_id }) => {
      try {
        return await client.get(`/match/aggregate/batch/${sample_batch_id}/all`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get aggregated matches for batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    batchExportPeakData: async ({ sample_batch_id }) => {
      try {
        return await client.get(`/sample/batches/${sample_batch_id}/export_peaks`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to export sample batch peaks: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    // Samples
    getAllSamples: async (params) => {
      try {
        return await client.get('/samples', { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get batch samples data: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getSample: async ({ sampleId }) => {
      try {
        return await client.get(`/samples/${sampleId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get the sample data: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Sample Files
    getAllSampleFiles: async (params = {}) => {
      try {
        return await client.get('/sample/files', { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all sample files: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getRecentSampleFiles: async (params = {}) => {
      try {
        return await client.get(`/sample/files/recent`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get recent acquisitions: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getSampleFile: async (sample_file_id) => {
      try {
        return await client.get(`/sample/files/${sample_file_id}`)
      } catch (error) {
        console.error('Failed to get sample file: ', error)
      }
    },
    createSampleFile: async (newSampleFile) => {
      try {
        return await client.post('/sample/files', newSampleFile)
      } catch (error) {
        console.error('Failed to create sample file: ', error)
      }
    },
    deleteSampleFile: async (sample_file_id) => {
      try {
        return await client.delete(`/sample/files/${sample_file_id}`)
      } catch (error) {
        console.error('Failed to delete sample file: ', error)
      }
    },
    updateSampleFile: async (sample_file_id, updatedSampleFile) => {
      try {
        return await client.patch(`/sample/files/${sample_file_id}`, updatedSampleFile)
      } catch (error) {
        console.error('Failed to update sample file: ', error)
      }
    },
    getSampleSpectrum: async ({ sample_file_id }) => {
      try {
        return await client.get(`/sample/files/${sample_file_id}/spectrum`)
      } catch (error) {
        console.error('Failed to get sample spectrum: ', error)
      }
    },

    // Sample Items
    getAllSampleItems: async (params = {}) => {
      try {
        return await client.get('/sample/items', { params })
      } catch (error) {
        console.error('Failed to get all sample items: ', error)
      }
    },
    getSampleItem: async (sample_item_id) => {
      try {
        return await client.get(`/sample/items/${sample_item_id}`)
      } catch (error) {
        console.error('Failed to get sample item: ', error)
      }
    },

    createSampleItem: async (sample) => {
      try {
        return await client.post('/sample/items', sample)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create sample item ${sample.sample_item_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    processSampleItem: async ({ sample, mz_calibration_params }) => {
      try {
        return await client.post(`/sample/items/process`, {
          sample_item: sample,
          mz_calibration_params: mz_calibration_params
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
        return await client.patch(`/sample/items/${sampleId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update sample item ${body.sample_item_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    deleteSampleItem: async ({ sampleId }) => {
      try {
        return await client.delete(`/sample/items/${sampleId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to delete sample item: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    copySampleItem: async ({ sampleId, body }) => {
      try {
        return await client.post(`/sample/items/${sampleId}/copy`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to copy sample item: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Calibration
    getMzCalibration: async (params) => {
      try {
        return await client.get(`/calibration/mz_calibration`, {
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
        return await client.post(`/calibration/mz_fit`, body, config)
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

        return await client.post(`/calibration/mz_apply`, body, config)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to apply mz calibration for '${filename}': ${error}`
        throw new Error(userErrorMessage)
      }
    },

    calibrationMzCalibrateSample: async ({ sampleId, sampleName, body }) => {
      try {
        return await client.post(`/calibration/mz_calibrate/sample/${sampleId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to m/z calibrate sample '${sampleName}': ${error}`
        throw new Error(userErrorMessage)
      }
    },

    calibrationMzCalibrateBatch: async ({ batch, body }) => {
      try {
        return await client.post(`/calibration/mz_calibrate/batch/${batch.sample_batch_id}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to m/z calibrate sample batch '${batch.sample_batch_name}': ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Match
    rematchBatch: async ({ batchId, body = {} }) => {
      try {
        return await client.post(`/match/rematch/batch/${batchId}`, body)
      } catch (error) {
        const userErrorMessage = error?.response?.data?.error || `Failed to rematch batch: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    matchSampleCompute: async ({ sampleId, body = {} }) => {
      try {
        return await client.post(`/match/compute/sample/${sampleId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to compute mathes for sample: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    rematchSample: async ({ sampleId, body = {} }) => {
      try {
        return await client.post(`/match/rematch/sample/${sampleId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to rematch sample: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // MatchIsotopes
    getAllMatchIsotopes: async (params = {}) => {
      try {
        return await client.get(`/match/isotopes`, { params })
      } catch (error) {
        const userErrorMessage = error?.response?.data?.error || `Failed to get matches: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getMatchIsotope: async (matchId) => {
      try {
        return await client.get(`/match/isotopes/${matchId}`)
      } catch (error) {
        console.error('Failed to get match isotope: ', error)
      }
    },

    // Match interferences
    getAllMatchInterferences: async (params = {}) => {
      try {
        return await client.get(`/match/interferences`, { params })
      } catch (error) {
        console.error('Failed to get all match interferences: ', error)
      }
    },
    getMatchInterference: async (interferenceId) => {
      try {
        return await client.get(`/match/interferences/${interferenceId}`)
      } catch (error) {
        console.error('Failed to get match interference by id: ', error)
      }
    },

    // Match Ratings
    submitMatchRating: async (newMatchRating) => {
      try {
        return await client.post('/match_ratings', newMatchRating)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to submit match rating: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Match batch targets
    getBatchMatchCollections: async ({ sample_batch_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/batch/${sample_batch_id}/collections`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve batch match collections (batch id ${sample_batch_id}): ${error}`
        )
      }
    },
    getBatchMatchCompounds: async ({ sample_batch_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/batch/${sample_batch_id}/compounds`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve batch match compounds (batch id ${sample_batch_id}): ${error}`
        )
      }
    },
    getBatchMatchIons: async ({ sample_batch_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/batch/${sample_batch_id}/ions`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve batch match ions (batch id ${sample_batch_id}): ${error}`
        )
      }
    },
    getBatchMatchIsotopes: async ({ sample_batch_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/batch/${sample_batch_id}/isotopes`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve batch match isotopes (batch id ${sample_batch_id}): ${error}`
        )
      }
    },
    // Match sample targets
    getSampleMatchCollections: async ({ sample_item_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/sample/${sample_item_id}/collections`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve sample match collections (sample id ${sample_item_id}): ${error}`
        )
      }
    },
    getSampleMatchCompounds: async ({ sample_item_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/sample/${sample_item_id}/compounds`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve sample match compounds (sample id ${sample_item_id}): ${error}`
        )
      }
    },
    getSampleMatchIons: async ({ sample_item_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/sample/${sample_item_id}/ions`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve sample match ions (sample id ${sample_item_id}): ${error}`
        )
      }
    },
    getSampleMatchIsotopes: async ({ sample_item_id, params = {} }) => {
      try {
        return await client.get(`/match/targets/sample/${sample_item_id}/isotopes`, { params })
      } catch (error) {
        throw new Error(
          error?.response?.data?.error ??
            `Failed to retrieve sample match isotopes (sample id ${sample_item_id}): ${error}`
        )
      }
    },

    // Match sample aggregates
    getAggregateSampleMatchIon: async ({ sampleId, body = {} }) => {
      try {
        return await client.post(`/match/aggregate/sample/${sampleId}/ion`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get sample ion match data: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    // Target collections
    getAllTargetCollections: async (params = {}) => {
      try {
        return await client.get(`/target/collections`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all target collections: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getTargetCollection: async (collectionId) => {
      try {
        return await client.get(`/target/collections/${collectionId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get target collection: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    createTargetCollection: async (newCollection) => {
      try {
        return await client.post('/target/collections', newCollection)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create target collection ${newCollection.target_collection_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    updateTargetCollection: async ({ collectionId, body }) => {
      try {
        return await client.patch(`/target/collections/${collectionId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update target collection ${body.target_collection_name}: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    deleteTargetCollection: async ({ collectionId, collectionName, deleteOrphanCompounds }) => {
      try {
        return await client.delete(`/target/collections/${collectionId}`, {
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
        return await client.get('/target/associations/target_collections_in_sample_batch', {
          params
        })
      } catch (error) {
        console.error('Failed to get target collections in sample batch: ', error)
      }
    },

    // Target compounds
    getAllTargetCompounds: async (params = {}) => {
      try {
        return await client.get(`/target/compounds`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all target compounds: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getTargetCompound: async (targetCompoundId) => {
      try {
        return await client.get(`/target/compounds/${targetCompoundId}`)
      } catch (error) {
        console.error('Failed to get target compound by id: ', error)
      }
    },

    createTargetCompounds: async (targetCompounds) => {
      try {
        return await client.post('/target/compounds', targetCompounds)
      } catch (error) {
        console.error('Failed to create target compounds: ', error)
      }
    },
    updateTargetCompounds: async (targetCompounds) => {
      try {
        return await client.patch('/target/compounds', targetCompounds)
      } catch (error) {
        console.error('Failed to update target compounds: ', error)
      }
    },
    deleteTargetCompound: async (targetCompoundId) => {
      try {
        return await client.delete(`/target/compounds/${targetCompoundId}`)
      } catch (error) {
        console.error('Failed to delete target compound: ', error)
      }
    },

    // Target compound in target collections
    getAllTargetCompoundsInTargetCollection: async (params = {}) => {
      try {
        return await client.get('/target/associations/target_compound_in_target_collections', {
          params
        })
      } catch (error) {
        console.error('Failed to get all target compound in target collections: ', error)
      }
    },

    // Target ions
    getAllTargetIons: async (params = {}) => {
      try {
        return await client.get('/target/ions', { params })
      } catch (error) {
        console.error('Failed to get all target ions: ', error)
      }
    },

    getTargetIon: async (targetIonId) => {
      try {
        return await client.get(`/target/ions/${targetIonId}`)
      } catch (error) {
        console.error('Failed to get target ion: ', error)
      }
    },
    updateTargetIon: async (data) => {
      try {
        return await client.patch(`/target/ions/${data.target_ion_id}`, data.body)
      } catch (error) {
        console.error(`Failed to update target ion ${data.target_ion_formula}`, error)
      }
    },
    saveTargetIonFilterParams: async (data) => {
      try {
        const response = await client.patch(`/target/ions/${data.target_ion_id}`, data.body)
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
        const response = await client.patch(`/target/ions/${data.target_ion_id}`, data.body)
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
        return await client.get('/ionization_mechanisms', {
          params
        })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get all ionization mechanisms: ${error}`
        throw new Error(userErrorMessage)
      }
    },

    getIonizationMechanism: async (ionizationMechanismId) => {
      try {
        return await client.get(`/ionization_mechanisms/${ionizationMechanismId}`)
      } catch (error) {
        console.error('Failed to get ionization mechanism by id: ', error)
      }
    },
    // Target isotopes
    getAllTargetIsotopes: async (params = {}) => {
      try {
        return await client.get(`/target/isotopes`, { params })
      } catch (error) {
        console.error('Failed to get all target isotopes: ', error)
      }
    },
    getTargetIsotope: async (isotopeId) => {
      try {
        return await client.get(`/target/isotopes/${isotopeId}`)
      } catch (error) {
        console.error('Failed to get target isotope by id: ', error)
      }
    },

    // Instrument functions
    getAllInstrumentFunctions: async (params = {}) => {
      try {
        return await client.get(`/instrument_functions`, {
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
        return await client.get(`/instrument_functions/`, {
          params
        })
      } catch (error) {
        console.error('Failed to get instrument function by id: ', error)
      }
    },

    // Attribute templates
    getAllAttributeTemplates: async (params = {}) => {
      try {
        return await client.get(`/attribute_templates`, { params })
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to get attribute templates: ${error}`
        throw new Error(userErrorMessage)
      }
    },
    getAttributeTemplate: async (templateId) => {
      try {
        return await client.get(`/attribute_templates/${templateId}`)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to get attribute template with ID "${templateId}": ${error}`
        throw new Error(userErrorMessage)
      }
    },
    createAttributeTemplate: async (newTemplate) => {
      try {
        return await client.post('/attribute_templates', newTemplate)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create attribute template "${newTemplate.name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },

    updateAttributeTemplate: async ({ templateId, body }) => {
      try {
        return await client.patch(`/attribute_templates/${templateId}`, body)
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update attribute template "${body.name}": ${error}`
        throw new Error(userErrorMessage)
      }
    },

    deleteAttributeTemplate: async ({ templateId, templateName }) => {
      try {
        return await client.delete(`/attribute_templates/${templateId}`)
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
        return await client.get(`/visualization/ion_focus`, {
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
