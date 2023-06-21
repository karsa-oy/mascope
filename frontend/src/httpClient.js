import axios from "axios";
import Vue from "vue";

const logRequest = (request) => {
  console.log(
    `[httpClient] Starting request to: ${request.method.toUpperCase()} ${
      request.url
    }`
  );
  return request;
};

const logResponse = (response) => {
  console.log(
    `[httpClient] Response: ${response.status} ${
      response.statusText
    } from ${response.config.method.toUpperCase()} ${response.config.url}`
  );
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

const openLoading = () => {
  return Vue.prototype.$buefy.loading.open();
};

const workspacesBaseUrl = "/workspaces";
const batchesBaseUrl = "/sample_batches";
const filesBaseUrl = "/sample_files";
const itemsBaseUrl = "/sample_items";
const calibrationBaseUrl = "/calibration";
const matchesBaseUrl = "/matches";
const targetCollectionsBaseUrl = "/target_collections";
const targetCollectionsInSampleBatchBaseUrl =
  "/target_collections_in_sample_batch";
const targetCompoundsBaseUrl = "/target_compounds";
const targetCompoundsInTargetCollectionsBaseUrl =
  "/target_compound_in_target_collections";
const targetIonsBaseUrl = "/target_ions";
const ionizationMechanismsBaseUrl = "/ionization_mechanisms";
const targetIsotopesBaseUrl = "/target_isotopes";
const matchInterferencesBaseUrl = "/match_interferences";
const instrumentFunctionsBaseUrl = "/instrument_functions";
const attributeTemplatesBaseUrl = "/attribute_templates";

export function createHttpClient(host, api_port) {
  const axiosInstance = axios.create({
    baseURL: `http://${host}:${api_port}/api`,
    timeout: 15000,
  });
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
    getWorkspaceById: async (workspace_id) => {
      try {
        return await httpClient.get(`${workspacesBaseUrl}/${workspace_id}`);
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
    deleteWorkspace: async (workspace_id) => {
      try {
        return await httpClient.delete(`${workspacesBaseUrl}/${workspace_id}`);
      } catch (error) {
        console.error("Failed to delete workspace: ", error);
      }
    },
    updateWorkspace: async (workspace_id, updatedWorkspace) => {
      try {
        return await httpClient.patch(
          `${workspacesBaseUrl}/${workspace_id}`,
          updatedWorkspace
        );
      } catch (error) {
        console.error("Failed to update workspace: ", error);
      }
    },
    loadWorkspace: async (workspace_id) => {
      try {
        const response = await httpClient.get(
          `${batchesBaseUrl}?workspace_id=${workspace_id}`
        );
        return response;
      } catch (error) {
        console.error("Failed to fetch sample batches: ", error);
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
    getBatchById: async (sample_batch_id) => {
      try {
        return await httpClient.get(`${batchesBaseUrl}/${sample_batch_id}`);
      } catch (error) {
        console.error("Failed to get batch: ", error);
      }
    },
    createBatch: async (newBatch) => {
      try {
        return await httpClient.post(batchesBaseUrl, newBatch);
      } catch (error) {
        console.error("Failed to create sample batch: ", error);
      }
    },
    deleteBatch: async (batches) => {
      try {
        const promises = batches.map((batch) =>
          httpClient.delete(`${batchesBaseUrl}/${batch}`)
        );
        const results = await Promise.allSettled(promises);
        return results.map((result, index) => {
          if (result.status === "rejected") {
            throw new Error(
              `Failed to delete batch with id ${batches[index]}: ${result.reason}`
            );
          } else {
            return result.value;
          }
        });
      } catch (error) {
        console.error("Failed to delete batches: ", error);
      }
    },
    updateBatch: async (newBatch) => {
      try {
        return await httpClient.patch(
          `${batchesBaseUrl}/${newBatch.sample_batch_id}`,
          newBatch
        );
      } catch (error) {
        console.error("Failed to update batch", error);
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

    // Calibration
    getLastMzCalibration: async (params = {}) => {
      try {
        return await httpClient.get(
          `${calibrationBaseUrl}/last_mz_calibration`,
          {
            params,
          }
        );
      } catch (error) {
        console.error("Failed to get last mz calibration: ", error);
      }
    },
    mzCalibrationApply: async (calibrationData, showLoading = false) => {
      let loadingInstance = null;
      try {
        if (showLoading) loadingInstance = openLoading();
        const result = await httpClient.post(
          `${calibrationBaseUrl}/mz_apply`,
          calibrationData
        );
        if (loadingInstance)
          setTimeout(() => loadingInstance.close(), 1 * 1000);
        return result;
      } catch (error) {
        console.error("Failed to apply mz calibration: ", error);
        if (loadingInstance) loadingInstance.close();
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

    // Target collections
    getAllTargetCollections: async (params = {}) => {
      try {
        return await httpClient.get(`${targetCollectionsBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all target collections: ", error);
      }
    },

    getTargetCollectionById: async (targetCollectionId) => {
      try {
        return await httpClient.get(
          `${targetCollectionsBaseUrl}/${targetCollectionId}`
        );
      } catch (error) {
        console.error("Failed to get target collection by id: ", error);
      }
    },

    // Target collections in sample batch
    getAllTargetCollectionsInSampleBatch: async (params = {}) => {
      try {
        return await httpClient.get(
          `${targetCollectionsInSampleBatchBaseUrl}`,
          {
            params,
          }
        );
      } catch (error) {
        console.error(
          "Failed to get all target collections in sample batch: ",
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

    // Target compound in target collections
    getAllTargetCompoundInTargetCollections: async (params = {}) => {
      try {
        return await httpClient.get(
          `${targetCompoundsInTargetCollectionsBaseUrl}`,
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

    getTargetIonById: async (targetIonId) => {
      try {
        return await httpClient.get(`${targetIonsBaseUrl}/${targetIonId}`);
      } catch (error) {
        console.error("Failed to get target ion by id: ", error);
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
    getInstrumentFunctionById: async (functionId) => {
      try {
        return await httpClient.get(
          `${instrumentFunctionsBaseUrl}/${functionId}`
        );
      } catch (error) {
        console.error("Failed to get instrument function by id: ", error);
      }
    },

    // Attribute templates
    getAllAttributeTemplates: async (params = {}) => {
      try {
        return await httpClient.get(`${attributeTemplatesBaseUrl}`, { params });
      } catch (error) {
        console.error("Failed to get all attribute templates: ", error);
      }
    },
    getAttributeTemplateById: async (templateId) => {
      try {
        return await httpClient.get(
          `${attributeTemplatesBaseUrl}/${templateId}`
        );
      } catch (error) {
        console.error("Failed to get attribute template by id: ", error);
      }
    },
  };

  return httpClient;
}
