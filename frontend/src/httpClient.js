import axios from "axios";

const host = location.hostname;
const api_port = import.meta.env.MASCOPE_PUBLIC_API_PORT;

export const httpClient = axios.create({
  baseURL: `http://${host}:${api_port}/api`,
  timeout: 15000,
});

export default {
  // Workspaces
  getAllWorkspaces: async (params = {}) => {
    try {
      return await httpClient.get("/workspaces", { params });
    } catch (error) {
      console.error("Failed to get all workspaces: ", error);
    }
  },
  getWorkspaceById: async (workspace_id) => {
    try {
      return await httpClient.get(`/workspaces/${workspace_id}`);
    } catch (error) {
      console.error("Failed to get workspace: ", error);
    }
  },
  createWorkspace: async (newWorkspace) => {
    try {
      return await httpClient.post("/workspaces", newWorkspace);
    } catch (error) {
      console.error("Failed to create workspace: ", error);
    }
  },
  deleteWorkspace: async (workspace_id) => {
    try {
      return await httpClient.delete(`/workspaces/${workspace_id}`);
    } catch (error) {
      console.error("Failed to delete workspace: ", error);
    }
  },
  updateWorkspace: async (workspace_id, updatedWorkspace) => {
    try {
      return await httpClient.patch(
        `/workspaces/${workspace_id}`,
        updatedWorkspace
      );
    } catch (error) {
      console.error("Failed to update workspace: ", error);
    }
  },
  loadWorkspace: async (workspace_id) => {
    try {
      const response = await httpClient.get(
        `/sample_batches?workspace_id=${workspace_id}`
      );
      return response;
    } catch (error) {
      console.error("Failed to fetch sample batches: ", error);
    }
  },
  // Sample batches
  getAllBatches: async (params = {}) => {
    try {
      return await httpClient.get("/sample_batches", { params });
    } catch (error) {
      console.error("Failed to get all sample batches: ", error);
    }
  },
  getBatchById: async (sample_batch_id) => {
    try {
      return await httpClient.get(`/sample_batches/${sample_batch_id}`);
    } catch (error) {
      console.error("Failed to get batch: ", error);
    }
  },
  createBatch: async (newBatch) => {
    try {
      return await httpClient.post("/sample_batches", newBatch);
    } catch (error) {
      console.error("Failed to create sample batch: ", error);
    }
  },
  deleteBatch: async (batches) => {
    try {
      const promises = batches.map((batch) =>
        httpClient.delete(`/sample_batches/${batch}`)
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
        `/sample_batches/${newBatch.sample_batch_id}`,
        newBatch
      );
    } catch (error) {
      console.error("Failed to update batch", error);
    }
  },

  // Sample Files
  getAllSampleFiles: async (params = {}) => {
    try {
      return await httpClient.get("/sample_files", { params });
    } catch (error) {
      console.error("Failed to get all sample files: ", error);
    }
  },
  getRecentSampleFiles: async (params = {}) => {
    try {
      return await httpClient.get("/sample_files/recent", { params });
    } catch (error) {
      console.error("Failed to get recent acquisitions: ", error);
    }
  },
  getSampleFileById: async (sample_file_id) => {
    try {
      return await httpClient.get(`/sample_files/${sample_file_id}`);
    } catch (error) {
      console.error("Failed to get sample file: ", error);
    }
  },
  createSampleFile: async (newSampleFile) => {
    try {
      return await httpClient.post("/sample_files", newSampleFile);
    } catch (error) {
      console.error("Failed to create sample file: ", error);
    }
  },
  deleteSampleFile: async (sample_file_id) => {
    try {
      return await httpClient.delete(`/sample_files/${sample_file_id}`);
    } catch (error) {
      console.error("Failed to delete sample file: ", error);
    }
  },
  updateSampleFile: async (sample_file_id, updatedSampleFile) => {
    try {
      return await httpClient.patch(
        `/sample_files/${sample_file_id}`,
        updatedSampleFile
      );
    } catch (error) {
      console.error("Failed to update sample file: ", error);
    }
  },
  // TODO move to calibration + in backend
  getLastMzCalibration: async (params = {}) => {
    try {
      return await httpClient.get("/sample_files/mz_calibration", { params });
    } catch (error) {
      console.error("Failed to get last mz calibration: ", error);
    }
  },

  // Sample Items
  getAllSampleItems: async (params = {}) => {
    try {
      return await httpClient.get("/sample_items", { params });
    } catch (error) {
      console.error("Failed to get all sample items: ", error);
    }
  },
  getSampleItemById: async (sample_item_id) => {
    try {
      return await httpClient.get(`/sample_items/${sample_item_id}`);
    } catch (error) {
      console.error("Failed to get sample item: ", error);
    }
  },

  // Calibration
  mzCalibrationApply: async (calibrationData) => {
    try {
      return await httpClient.post("/calibration/mz_apply", calibrationData);
    } catch (error) {
      console.error("Failed to apply mz calibration: ", error);
    }
  },
};
