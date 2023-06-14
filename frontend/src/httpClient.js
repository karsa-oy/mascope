import axios from "axios";

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

const workspacesBaseUrl = "/workspaces";
const batchesBaseUrl = "/sample_batches";
const filesBaseUrl = "/sample_files";
const itemsBaseUrl = "/sample_items";
const calibrationBaseUrl = "/calibration";

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
        return await httpClient.get(`${filesBaseUrl}/recent`, { params });
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
    mzCalibrationApply: async (calibrationData) => {
      try {
        return await httpClient.post(
          `${calibrationBaseUrl}/mz_apply`,
          calibrationData
        );
      } catch (error) {
        console.error("Failed to apply mz calibration: ", error);
      }
    },
  };

  return httpClient;
}
