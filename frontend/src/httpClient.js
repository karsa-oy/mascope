import axios from "axios";
import Vue from "vue";

// Create the URL

// LOAD ENV VARS
const mode = import.meta.env.MASCOPE_PUBLIC_MODE;
const host = location.hostname;
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT;

// production api server is routed to api_port via nginx reverse proxy
let url =
  mode === "production" ? `http://${host}` : `http://${host}:${api_port}`;

const getSessionId = () => {
  // get session id for emitting sio finished events
  const sid = Vue.prototype.$api.socket.id;
  return sid;
};

const logRequest = (request) => {
  console.log(
    `[httpClient] Starting request to: ${request.method.toUpperCase()} ${
      request.url
    }`
  );
  return request;
};

const logResponse = (response) => {
  let logMessage = `[httpClient] Response: ${response.status} ${
    response.statusText
  } from ${response.config.method.toUpperCase()} ${response.config.url}`;
  // Append the message if available
  if (response.data && response.data.message) {
    logMessage += ` | Message: ${response.data.message}`;
  }

  console.log(logMessage);

  // Log the message-logs if available
  if (response.data && response.data["message-logs"]) {
    console.log(`[httpClient] Message-Logs:`, response.data["message-logs"]);
  }

  return response;
};

const handleError = (error) => {
  if (error.response) {
    console.log(
      `[httpClient] Response Error: ${error.response.status} ${error.response.statusText}`
    );
  } else {
    console.log(`[httpClient] Request Error: ${error.message}`);
  }
  return Promise.reject(error);
};

const workspacesBaseUrl = "/workspaces";
const batchesBaseUrl = "/sample_batches";
const samplesBaseUrl = "/samples";
const filesBaseUrl = "/sample_files";
const itemsBaseUrl = "/sample_items";
const calibrationBaseUrl = "/calibration";
const matchBaseUrl = "/match";
const matchesBaseUrl = "/matches";
const matchRatingsBaseUrl = "/match_ratings";
const targetCollectionsBaseUrl = "/target_collections";
const targetCollectionsInSampleBatchBaseUrl =
  "/target_collections_in_sample_batch";
const targetCompoundsBaseUrl = "/target_compounds";
const targetCompoundsInTargetCollectionBaseUrl =
  "/target_compound_in_target_collections";
const targetIonsBaseUrl = "/target_ions";
const ionizationMechanismsBaseUrl = "/ionization_mechanisms";
const targetIsotopesBaseUrl = "/target_isotopes";
const matchInterferencesBaseUrl = "/match_interferences";
const instrumentFunctionsBaseUrl = "/instrument_functions";
const attributeTemplatesBaseUrl = "/attribute_templates";

export function createHttpClient(host, api_port) {
  const axiosInstance = axios.create({
    baseURL: `${url}/api`,
    timeout: 20000,
  });

  // Request interceptor to add X-SID header to every request, 'X-' prefix is a convention for custom headers
  axiosInstance.interceptors.request.use(
    (config) => {
      const sid = getSessionId();
      if (sid) {
        config.headers["X-SID"] = sid;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
  // Interceptor to log requests and responses
  axiosInstance.interceptors.request.use(logRequest);
  axiosInstance.interceptors.response.use(logResponse, handleError);

  const httpClient = {
    ...axiosInstance,
    // Workspaces
    getAllWorkspaces: async (params = {}) => {
      try {
        return await httpClient.get(workspacesBaseUrl, { params });
      } catch (error) {
        console.error("Failed to get all workspaces: ", error);
      }
    },
    getWorkspace: async (workspaceId) => {
      try {
        return await httpClient.get(`${workspacesBaseUrl}/${workspaceId}`);
      } catch (error) {
        console.error("Failed to get workspace: ", error);
      }
    },
    createWorkspace: async (newWorkspace) => {
      try {
        return await httpClient.post(workspacesBaseUrl, newWorkspace);
      } catch (error) {
        console.error("Failed to create workspace: ", error);
      }
    },
    deleteWorkspace: async (workspace) => {
      try {
        return await httpClient.delete(
          `${workspacesBaseUrl}/${workspace.workspace_id}`
        );
      } catch (error) {
        console.error(
          `Failed to delete workspace ${workspace.workspace_name}: `,
          error
        );
      }
    },
    updateWorkspace: async (newWorkspace) => {
      try {
        return await httpClient.patch(
          `${workspacesBaseUrl}/${newWorkspace.workspace_id}`,
          newWorkspace
        );
      } catch (error) {
        console.error(
          `Failed to update workspace ${newWorkspace.workspace_name}: `,
          error
        );
      }
    },
    // Sample batches
    getAllBatches: async (params = {}) => {
      try {
        return await httpClient.get(batchesBaseUrl, { params });
      } catch (error) {
        console.error("Failed to get all sample batches: ", error);
      }
    },
    getBatch: async (batchId) => {
      try {
        return await httpClient.get(`${batchesBaseUrl}/${batchId}`);
      } catch (error) {
        console.error("Failed to get batch: ", error);
      }
    },
    getBatchTargets: async ({ batchId, body }) => {
      try {
        return await httpClient.post(
          `${batchesBaseUrl}/${batchId}/targets`,
          body
        );
      } catch (error) {
        console.error("Failed to fetch batch targets: ", error);
      }
    },
    createBatch: async (newBatch) => {
      try {
        return await httpClient.post(batchesBaseUrl, newBatch);
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create sample batch "${newBatch.sample_batch_name}": ${error}`;
        throw new Error(userErrorMessage);
      }
    },
    deleteBatch: async (batch) => {
      try {
        return await httpClient.delete(
          `${batchesBaseUrl}/${batch.sample_batch_id}`
        );
      } catch (error) {
        console.error(
          `Failed to delete batch "${batch.sample_batch_name}".`,
          error
        );
      }
    },
    updateBatch: async ({ batchId, body }) => {
      try {
        return await httpClient.patch(`${batchesBaseUrl}/${batchId}`, body);
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update sample batch "${body.sample_batch_name}": ${error}`;
        throw new Error(userErrorMessage);
      }
    },
    importSamplesToBatch: async ({ batch, body }) => {
      try {
        return await httpClient.post(
          `${batchesBaseUrl}/${batch.sample_batch_id}/import`,
          body
        );
      } catch (error) {
        // TODO_error_handling
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to import sample batch: ${error}`;
        throw new Error(userErrorMessage);
      }
    },
    copySampleBatch: async ({ batchId, body }) => {
      try {
        return await httpClient.post(`${batchesBaseUrl}/${batchId}/copy`, body);
      } catch (error) {
        // TODO_error_handling
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to copy sample batch: ${error}`;
        throw new Error(userErrorMessage);
      }
    },
    batchExportPeakData: async (sampleBatchData) => {
      try {
        return await httpClient.post(
          `${batchesBaseUrl}/export_peaks`,
          sampleBatchData
        );
      } catch (error) {
        console.error("Failed to export sample batch peaks: ", error);
      }
    },
    // Samples
    getAllSamples: async (body) => {
      try {
        return await httpClient.post(samplesBaseUrl, body);
      } catch (error) {
        console.error("Failed to get all samples: ", error);
      }
    },

    getSample: async ({ sampleId, body }) => {
      try {
        return await httpClient.post(`${samplesBaseUrl}/${sampleId}`, body);
      } catch (error) {
        console.error("Failed to get sample: ", error);
      }
    },

    getSampleIonMatches: async ({ sampleId, body }) => {
      try {
        return await httpClient.post(
          `${samplesBaseUrl}/${sampleId}/ion_matches`,
          body
        );
      } catch (error) {
        console.error("Failed to get sample ion matches: ", error);
      }
    },

    getBatchMatchFilter: async (batchId) => {
      try {
        return await httpClient.get(
          `${samplesBaseUrl}/batch_match_filter/${batchId}`
        );
      } catch (error) {
        console.error("Failed to initialize batch match filter: ", error);
      }
    },

    getSampleMatchFilter: async (sampleItemId, body) => {
      try {
        return await httpClient.post(
          `${samplesBaseUrl}/${sampleItemId}/sample_match_filter`,
          body
        );
      } catch (error) {
        console.error("Failed to initialize sample match filter: ", error);
      }
    },

    // Sample Files
    getAllSampleFiles: async (params = {}) => {
      try {
        return await httpClient.get(filesBaseUrl, { params });
      } catch (error) {
        console.error("Failed to get all sample files: ", error);
      }
    },
    getRecentSampleFiles: async (params = {}) => {
      try {
        return await httpClient.get(`${filesBaseUrl}-recent`, { params });
      } catch (error) {
        console.error("Failed to get recent acquisitions: ", error);
      }
    },
    getSampleFileById: async (sample_file_id) => {
      try {
        return await httpClient.get(`${filesBaseUrl}/${sample_file_id}`);
      } catch (error) {
        console.error("Failed to get sample file: ", error);
      }
    },
    createSampleFile: async (newSampleFile) => {
      try {
        return await httpClient.post(filesBaseUrl, newSampleFile);
      } catch (error) {
        console.error("Failed to create sample file: ", error);
      }
    },
    deleteSampleFile: async (sample_file_id) => {
      try {
        return await httpClient.delete(`${filesBaseUrl}/${sample_file_id}`);
      } catch (error) {
        console.error("Failed to delete sample file: ", error);
      }
    },
    updateSampleFile: async (sample_file_id, updatedSampleFile) => {
      try {
        return await httpClient.patch(
          `${filesBaseUrl}/${sample_file_id}`,
          updatedSampleFile
        );
      } catch (error) {
        console.error("Failed to update sample file: ", error);
      }
    },

    // Sample Items
    getAllSampleItems: async (params = {}) => {
      try {
        return await httpClient.get(itemsBaseUrl, { params });
      } catch (error) {
        console.error("Failed to get all sample items: ", error);
      }
    },
    getSampleItemById: async (sample_item_id) => {
      try {
        return await httpClient.get(`${itemsBaseUrl}/${sample_item_id}`);
      } catch (error) {
        console.error("Failed to get sample item: ", error);
      }
    },

    createSampleItem: async (newSampleItem) => {
      try {
        return await httpClient.post(itemsBaseUrl, newSampleItem);
      } catch (error) {
        console.error("Failed to create sample item: ", error);
      }
    },
    updateSampleItem: async (sample_item_id, updatedSampleItem) => {
      try {
        return await httpClient.patch(
          `${itemsBaseUrl}/${sample_item_id}`,
          updatedSampleItem
        );
      } catch (error) {
        console.error("Failed to update sample item: ", error);
      }
    },
    deleteSampleItem: async (sample_item_id) => {
      try {
        return await httpClient.delete(`${itemsBaseUrl}/${sample_item_id}`);
      } catch (error) {
        console.error("Failed to delete sample item: ", error);
      }
    },
    copySampleItem: async ({ sampleId, body }) => {
      try {
        return await httpClient.post(`${itemsBaseUrl}/${sampleId}/copy`, body);
      } catch (error) {
        // TODO_error_handling
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to copy sample item: ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    // Calibration
    getMzCalibration: async (params) => {
      try {
        return await httpClient.get(`${calibrationBaseUrl}/mz_calibration`, {
          params,
        });
      } catch (error) {
        console.error("Failed to get mz calibration: ", error);
      }
    },
    calibrationMzFit: async ({ sampleId, sampleName, body }) => {
      try {
        const config = {
          params: {
            sample_item_id: sampleId,
          },
        };
        return await httpClient.post(
          `${calibrationBaseUrl}/mz_fit`,
          body,
          config
        );
      } catch (error) {
        console.error(
          `Failed to calibrate mz fit of sample ${sampleName}: `,
          error
        );
      }
    },

    calibrationMzApply: async ({ fit, sample_filename }) => {
      try {
        const config = {
          params: {
            sample_filename,
          },
        };
        const body = { fit };

        return await httpClient.post(
          `${calibrationBaseUrl}/mz_apply`,
          body,
          config
        );
      } catch (error) {
        console.error(
          `Failed to apply mz calibration for ${sample_filename}: `,
          error
        );
      }
    },

    calibrationMzCalibrateSample: async (sample_item, params) => {
      try {
        return await httpClient.post(
          `${calibrationBaseUrl}/mz_calibrate/sample`,
          {
            sample_item: sample_item,
            params: params,
          }
        );
      } catch (error) {
        console.error("Failed to m/z calibrate sample: ", error);
      }
    },

    calibrationMzCalibrateBatch: async ({ batch, body }) => {
      try {
        return await httpClient.post(
          `${calibrationBaseUrl}/mz_calibrate/batch/${batch.sample_batch_id}`,
          body
        );
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to m/z calibrate sample batch "${batch.sample_batch_name}": ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    // Matches
    getAllMatches: async (params = {}) => {
      try {
        return await httpClient.get(`${matchesBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all matches: ", error);
      }
    },
    getMatchById: async (matchId) => {
      try {
        return await httpClient.get(`${matchesBaseUrl}/${matchId}`);
      } catch (error) {
        console.error("Failed to get match by id: ", error);
      }
    },

    // Match
    rematchBatch: async ({ batchId, body = {} }) => {
      try {
        return await httpClient.post(
          `${matchBaseUrl}/batch/${batchId}/rematch`,
          body
        );
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error || `Failed to rematch batch: ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    matchSampleCompute: async ({ sampleId, body = {} }) => {
      try {
        return await httpClient.post(
          `${matchBaseUrl}/sample/${sampleId}/compute`,
          body
        );
      } catch (error) {
        console.error("Failed to compute mathes for sample: ", error);
      }
    },

    matchSampleRematch: async ({ sampleId, body = {} }) => {
      try {
        return await httpClient.post(
          `${matchBaseUrl}/sample/${sampleId}/rematch`,
          body
        );
      } catch (error) {
        console.error("Failed to rematch sample: ", error);
      }
    },

    // Match Ratings
    submitMatchRating: async (newMatchRating) => {
      try {
        return await httpClient.post(matchRatingsBaseUrl, newMatchRating);
      } catch (error) {
        console.error("Failed to submit match rating: ", error);
      }
    },

    // Target collections
    getAllTargetCollections: async (params = {}) => {
      try {
        return await httpClient.get(`${targetCollectionsBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all target collections: ", error);
      }
    },

    getTargetCollection: async (collectionId) => {
      try {
        return await httpClient.get(
          `${targetCollectionsBaseUrl}/${collectionId}`
        );
      } catch (error) {
        console.error("Failed to get target collection: ", error);
      }
    },

    createTargetCollection: async (newCollection) => {
      try {
        return await httpClient.post(targetCollectionsBaseUrl, newCollection);
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create target collection ${newCollection.target_collection_name}: ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    updateTargetCollection: async ({ collectionId, body }) => {
      try {
        return await httpClient.patch(
          `${targetCollectionsBaseUrl}/${collectionId}`,
          body
        );
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update target collection ${body.target_collection_name}: ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    deleteTargetCollection: async ({
      collectionId,
      collectionName,
      deleteOrphanCompounds,
    }) => {
      try {
        return await httpClient.delete(
          `${targetCollectionsBaseUrl}/${collectionId}`,
          {
            params: {
              delete_orphan_compounds: deleteOrphanCompounds,
            },
          }
        );
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete target collection ${collectionName}: ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    // Target Collections in Sample Batch
    getAllTargetCollectionsInSampleBatchByParams: async (params = {}) => {
      try {
        return await httpClient.get(targetCollectionsInSampleBatchBaseUrl, {
          params,
        });
      } catch (error) {
        console.error(
          "Failed to get target collections in sample batch: ",
          error
        );
      }
    },

    // Target compounds
    getAllTargetCompounds: async (params = {}) => {
      try {
        return await httpClient.get(`${targetCompoundsBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all target compounds: ", error);
      }
    },

    getTargetCompoundById: async (targetCompoundId) => {
      try {
        return await httpClient.get(
          `${targetCompoundsBaseUrl}/${targetCompoundId}`
        );
      } catch (error) {
        console.error("Failed to get target compound by id: ", error);
      }
    },

    createTargetCompounds: async (targetCompounds) => {
      try {
        return await httpClient.post(targetCompoundsBaseUrl, targetCompounds);
      } catch (error) {
        console.error("Failed to create target compounds: ", error);
      }
    },
    updateTargetCompounds: async (targetCompounds) => {
      try {
        return await httpClient.patch(targetCompoundsBaseUrl, targetCompounds);
      } catch (error) {
        console.error("Failed to update target compounds: ", error);
      }
    },
    deleteTargetCompound: async (targetCompoundId) => {
      try {
        return await httpClient.delete(
          `${targetCompoundsBaseUrl}/${targetCompoundId}`
        );
      } catch (error) {
        console.error("Failed to delete target compound: ", error);
      }
    },

    // Target compound in target collections
    getAllTargetCompoundsInTargetCollection: async (params = {}) => {
      try {
        return await httpClient.get(
          `${targetCompoundsInTargetCollectionBaseUrl}`,
          {
            params,
          }
        );
      } catch (error) {
        console.error(
          "Failed to get all target compound in target collections: ",
          error
        );
      }
    },

    // Target ions
    getAllTargetIons: async (params = {}) => {
      try {
        return await httpClient.get(`${targetIonsBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all target ions: ", error);
      }
    },

    getTargetIon: async (targetIonId) => {
      try {
        return await httpClient.get(`${targetIonsBaseUrl}/${targetIonId}`);
      } catch (error) {
        console.error("Failed to get target ion: ", error);
      }
    },
    updateTargetIon: async (data) => {
      try {
        return await httpClient.patch(
          `${targetIonsBaseUrl}/${data.target_ion_id}`,
          data.body
        );
      } catch (error) {
        console.error(
          `Failed to update target ion ${data.target_ion_formula}`,
          error
        );
      }
    },

    // Ionization mechanisms
    getAllIonizationMechanisms: async (params = {}) => {
      try {
        return await httpClient.get(`${ionizationMechanismsBaseUrl}`, {
          params,
        });
      } catch (error) {
        console.error("Failed to get all ionization mechanisms: ", error);
      }
    },

    getIonizationMechanismById: async (ionizationMechanismId) => {
      try {
        return await httpClient.get(
          `${ionizationMechanismsBaseUrl}/${ionizationMechanismId}`
        );
      } catch (error) {
        console.error("Failed to get ionization mechanism by id: ", error);
      }
    },
    // Target isotopes
    getAllTargetIsotopes: async (params = {}) => {
      try {
        return await httpClient.get(`${targetIsotopesBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all target isotopes: ", error);
      }
    },
    getTargetIsotopeById: async (isotopeId) => {
      try {
        return await httpClient.get(`${targetIsotopesBaseUrl}/${isotopeId}`);
      } catch (error) {
        console.error("Failed to get target isotope by id: ", error);
      }
    },

    // Match interferences
    getAllMatchInterferences: async (params = {}) => {
      try {
        return await httpClient.get(`${matchInterferencesBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all match interferences: ", error);
      }
    },
    getMatchInterferenceById: async (interferenceId) => {
      try {
        return await httpClient.get(
          `${matchInterferencesBaseUrl}/${interferenceId}`
        );
      } catch (error) {
        console.error("Failed to get match interference by id: ", error);
      }
    },

    // Instrument functions
    getAllInstrumentFunctions: async (params = {}) => {
      try {
        return await httpClient.get(`${instrumentFunctionsBaseUrl}`, {
          params,
        });
      } catch (error) {
        console.error("Failed to get all instrument functions: ", error);
      }
    },
    getInstrumentFunction: async (params = {}) => {
      try {
        return await httpClient.get(`${instrumentFunctionsBaseUrl}/`, {
          params,
        });
      } catch (error) {
        console.error("Failed to get instrument function by id: ", error);
      }
    },

    // Attribute templates
    getAllAttributeTemplates: async (params = {}) => {
      try {
        return await httpClient.get(`${attributeTemplatesBaseUrl}`, { params });
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to get all attribute templates: ${error}`;
        throw new Error(userErrorMessage);
      }
    },
    getAttributeTemplate: async (templateId) => {
      try {
        return await httpClient.get(
          `${attributeTemplatesBaseUrl}/${templateId}`
        );
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to get attribute template with ID "${templateId}": ${error}`;
        throw new Error(userErrorMessage);
      }
    },
    createAttributeTemplate: async (newTemplate) => {
      try {
        return await httpClient.post(attributeTemplatesBaseUrl, newTemplate);
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to create attribute template "${newTemplate.name}": ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    updateAttributeTemplate: async ({ templateId, body }) => {
      try {
        return await httpClient.patch(
          `${attributeTemplatesBaseUrl}/${templateId}`,
          body
        );
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to update attribute template "${body.name}": ${error}`;
        throw new Error(userErrorMessage);
      }
    },

    deleteAttributeTemplate: async ({ templateId, templateName }) => {
      try {
        return await httpClient.delete(
          `${attributeTemplatesBaseUrl}/${templateId}`
        );
      } catch (error) {
        const userErrorMessage =
          error?.response?.data?.error ||
          `Failed to delete attribute template "${templateName}: ${error}`;
        throw new Error(userErrorMessage);
      }
    },
  };

  return httpClient;
}
