import { defineModule } from "./lib/module";

import { api } from "@/api";

import { useMzFit } from "@/lib/mzFit";
import { genId } from "@/lib/utils";

import { useUi } from "../ui";

import { useBatch } from "./batch";

const FILE_UPLOAD_TIMEOUT = 600_000;

export const useSample = defineModule({
  name: "sample",
  key: "sample_item_id",
  multiselect: true,
  useParent: useBatch,
  unfocusBefore: ["delete"],
  subscribe: ({ sample_file_id }) => sample_file_id,
  load: ({ sample_batch_id }) =>
    api.http.get(`/samples`, {
      params: {
        sample_batch_id,
        sort: "datetime_utc",
      },
      use: "read",
      type: "load_samples",
    }),
  create: (sample) =>
    api.http.post(`/sample/items`, sample, {
      use: "create",
      type: "create_sample",
    }),
  update: (sample) =>
    api.http.patch(`/sample/items/${sample.sample_item_id}`, sample, {
      use: "update",
      type: "update_sample",
    }),
  delete: ({ sample_item_id }) =>
    api.http.delete(`/sample/items/${sample_item_id}`, {
      use: "delete",
      type: "delete_sample",
    }),
  copy: ({ sample_item_id, sample_batch_id, sample_item_name }) =>
    api.http.post(
      `/sample/items/${sample_item_id}/copy`,
      {
        sample_batch_id,
        sample_item_name,
      },
      {
        use: "process",
        type: "copy_sample",
      },
    ),
  process: async ({ sample, method_file }) => {
    const mzFit = useMzFit();
    return await api.http.post(
      `/sample/items/process`,
      {
        sample_item: sample,
        method_file,
        mz_calibration_params: mzFit.mzCalibrationParams,
      },
      {
        use: "process",
        type: "process_samples",
      },
    );
  },
  match: ({ sample_item_id }) =>
    api.http.post(
      `/match/compute/sample/${sampleId}`,
      {
        sampleId: sample_item_id,
      },
      {
        use: "process",
        type: "compute_match_sample",
      },
    ),
  rematch: async ({ sample_item_id }) =>
    api.http.post(
      `/match/rematch/sample/${sample_item_id}`,
      {},
      {
        use: "process",
        type: "rematch_sample",
      },
    ),
  upload: async (files) => {
    const ui = useUi();
    const mainProcessId = genId(8); // Generate a unique ID for the overall upload process
    let successes = 0; // Counter to track the number of successful uploads
    let errors = 0; // Counter to track the number of failed uploads

    // Use Promise.all to handle multiple file uploads in parallel
    await Promise.all(
      files.map(async (file) => {
        const process_id = genId(8); // Generate a unique ID for each file upload
        try {
          // Make the upload request with progress tracking
          const response = await api.http.postForm(
            `/sample/files/upload`,
            {
              file, // The file being uploaded
            },
            {
              timeout: FILE_UPLOAD_TIMEOUT,
              onUploadProgress: (progressEvent) => {
                const percentCompleted = progressEvent.progress * 100; // Calculate progress percentage

                // Update the progress for the current file
                ui.notification.push({
                  type: "sample_file_upload",
                  process_id,
                  parent_id: mainProcessId,
                  status: "pending",
                  message: `${file.name} - ${percentCompleted.toFixed(2)}% uploaded`,
                  progress: percentCompleted,
                });
              },
            },
          );

          // If the upload is successful, send a success notification for this file
          if (response?.status === 201) {
            successes += 1;
            ui.notification.push({
              type: "sample_file_upload",
              process_id,
              parent_id: mainProcessId,
              status: "success",
              message: `File ${file.name} uploaded successfully!`,
              progress: 100,
            });
          }
        } catch (error) {
          // Handle upload errors for this specific file
          errors += 1;
          const errorMessage = `Failed to upload file ${file.name}: ${error.message}`;
          ui.notification.push({
            type: "sample_file_upload",
            process_id,
            parent_id: mainProcessId,
            status: "error",
            message: errorMessage,
          });
          console.error(
            `${op.operationId} upload failed for ${file.name}:`,
            error,
          );
        }
      }),
    );
    // Emit a summary notification based on the success and error counts
    if (successes > 0 && errors === 0) {
      // All uploads were successful
      const s = successes > 1 ? "s" : "";
      ui.notification.push({
        type: "sample_file_upload",
        status: "success",
        process_id: mainProcessId,
        progress: 100,
        message: `Successfully uploaded ${successes} file${s}`,
      });
    } else if (successes > 0 && errors > 0) {
      // Some uploads were successful, some failed
      const s = successes > 1 ? "s" : "";
      ui.notification.push({
        type: "sample_file_upload",
        status: "warning",
        process_id: mainProcessId,
        progress: 100,
        message: `Successfully uploaded ${successes} file${s}, but failed to upload ${errors} file${errors > 1 ? "s" : ""}`,
      });
    } else if (errors > 0) {
      // All uploads failed
      ui.notification.push({
        type: "sample_file_upload",
        status: "error",
        process_id: mainProcessId,
        progress: 100,
        message: `Failed to upload all ${errors} file${errors > 1 ? "s" : ""}`,
      });
    }
    return {
      data: null,
      resolved: true,
    };
  },
});
