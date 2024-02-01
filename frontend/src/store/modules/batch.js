import { make } from "vuex-pathify";
import { camelToSnakeCase } from "../../lib/util";
import { handleApiRequest, getApiData } from "./apiHelper";

const state = {
  active: null,
  // samples
  sampleItems: null,
  // targets
  targetCollections: null,
  targetCompounds: null,
  targetIons: null,
  targetIsotopes: null,
  // matches
  matchSamples: null,
  matchCompounds: null,
  matchIons: null,
  // build parameters
  paramCalibrationCollection: null,
  paramIonMechanisms: null,
};

const paramDefaults = {
  // build parameters
  paramCalibrationCollection: [],
  paramIonMechanisms: [],
};

// initialize parameter values in state with defaults
for (const field in state) {
  if (field.startsWith("param")) {
    state[field] = paramDefaults[field];
  }
}

export default {
  namespaced: true,
  state,
  mutations: {
    ...make.mutations(state),
    SET_COLLECTION_SELECTION: (state, { collectionId, selectionValue }) => {
      const collection = state.targetCollections.find(
        (coll) => coll.target_collection_id === collectionId
      );
      if (collection) collection.selection = selectionValue;
    },
  },
  actions: {
    // data loading
    async load({ rootState, state, dispatch }, batchId) {
      if (state.active) await dispatch("unload");
      rootState.api.emit("subscribe", batchId);
      await dispatch("loadBatch", batchId);
      await dispatch("loadBatchSamplesData", batchId);
      await dispatch("unpackParams");
      await dispatch("loadBatchTargets", batchId);
    },

    async loadBatch({ commit, dispatch }, batchId) {
      const batch = await dispatch("getBatch", batchId);
      await commit("SET_ACTIVE", batch);
    },

    async loadBatchSamplesData({ commit, dispatch }, batchId) {
      const batchData = await dispatch("getBatchSamplesData", batchId);

      batchData.data.forEach((row, i) => (row.index = (i + 1).toString()));
      commit("SET_SAMPLE_ITEMS", batchData.data);
      if (!batchData.batch_matches_info) return;
      commit("SET_MATCH_SAMPLES", batchData.batch_matches_info?.match_samples);
      commit(
        "SET_MATCH_COMPOUNDS",
        batchData.batch_matches_info?.match_compounds
      );
      commit("SET_MATCH_IONS", batchData.batch_matches_info?.match_ions);
    },

    async loadBatchTargets({ rootGetters, commit, dispatch }, batchId) {
      const batchTargetsData = await dispatch("getBatchTargets", batchId);

      let targetCollections = batchTargetsData.target_collections;

      const activeCollection = rootGetters["targets/activeCollection"];
      if (targetCollections) {
        targetCollections = targetCollections.map((coll) => {
          if (
            activeCollection &&
            activeCollection.target_collection_id === coll.target_collection_id
          ) {
            coll.selection = 2;
          } else {
            coll.selection = 0;
          }
          return coll;
        });
      }

      commit("SET_TARGET_COLLECTIONS", targetCollections);
      commit("SET_TARGET_COMPOUNDS", batchTargetsData.target_compounds);
      commit("SET_TARGET_IONS", batchTargetsData.target_ions);
      commit("SET_TARGET_ISOTOPES", batchTargetsData.target_isotopes);
    },

    async reload(
      { getters, rootState, state, dispatch, commit },
      batch = null
    ) {
      const batchToLoad = batch ? batch : state.active;
      if (!batchToLoad) return;

      await dispatch("unload", false);
      const batchToLoadId = batchToLoad.sample_batch_id;
      await dispatch("load", batchToLoadId);
      const activeSampleId = rootState.sample.active?.sample_item_id || null;
      if (activeSampleId) {
        const sample = getters["sampleItem"](activeSampleId);
        sample.selection = 3;
        await dispatch("sample/reload", sample, { root: true });
      }
      const activeCollection = rootState.targets.activeCollection;
      if (activeCollection) {
        const activeCollectionId = activeCollection.target_collection_id;
        const matchingCollection = state.targetCollections.find(
          (coll) => coll.target_collection_id === activeCollectionId
        );
        if (matchingCollection) {
          commit("SET_COLLECTION_SELECTION", {
            collectionId: activeCollectionId,
            selectionValue: 2,
          });
        } else {
          // Dispatch to targets module to update selection there as well
          dispatch(
            "targets/updateCollectionSelection",
            {
              collectionId: activeCollectionId,
              selectionValue: 0,
            },
            { root: true }
          );
        }
      }
    },
    async unload({ rootState, commit, dispatch }, propagate = true) {
      if (!state.active) return;
      rootState.api.emit("unsubscribe", state.active.sample_batch_id);
      commit("SET_ACTIVE", null);
      // parameters
      dispatch("resetParams");
      // samples
      commit("SET_SAMPLE_ITEMS", null);
      // targets
      commit("SET_TARGET_COLLECTIONS", null);
      commit("SET_TARGET_COMPOUNDS", null);
      commit("SET_TARGET_IONS", null);
      commit("SET_TARGET_ISOTOPES", null);
      // matches
      commit("SET_MATCH_SAMPLES", null);
      commit("SET_MATCH_COMPOUNDS", null);
      commit("SET_MATCH_IONS", null);
      if (propagate) dispatch("sample/unload", null, { root: true });
    },

    // parameters
    async resetParams({ state, commit }) {
      // reset parameters to default values
      for (const field in state) {
        if (field.startsWith("param")) {
          const defaultValue = paramDefaults[field];
          commit(`SET_${camelToSnakeCase(field).toUpperCase()}`, defaultValue);
        }
      }
    },
    async unpackParams({ state, commit }) {
      // unpack parameters from batch object into state variables
      const buildParams = state.active.build_params;
      for (const param in buildParams) {
        await commit(`SET_PARAM_${param.toUpperCase()}`, buildParams[param]);
      }
    },

    // http client endpoints
    async getBatch({ dispatch }, batchId) {
      return await getApiData({
        dispatch,
        httpMethod: "getBatch",
        requestData: batchId,
        errorMessage: `Failed to load batch.`,
      });
    },

    async getBatchSamplesData({ dispatch, rootGetters }, batchId) {
      const alarmsList = rootGetters["targets/alarmsList"];

      const body = {
        sample_batch_id: batchId,
        batch_matches_info: true,
        sort: "datetime_utc",
        order: "asc",
        alarms_list: alarmsList,
      };

      return await getApiData({
        dispatch,
        httpMethod: "getAllSamples",
        requestData: body,
        errorMessage: `Failed to load batch samples data.`,
      });
    },

    async getBatchTargets({ state, dispatch, rootGetters }, batchId) {
      const alarmsList = rootGetters["targets/alarmsList"];

      const reqData = {
        batchId,
        body: {
          alarms_list: alarmsList,
        },
      };
      const batchTargetsData = await getApiData({
        dispatch,
        httpMethod: "getBatchTargets",
        requestData: reqData,
        errorMessage: `Failed to get batch targets.`,
      });

      return batchTargetsData.data;
    },

    async autoSamplerImportBatch({ rootState }, data) {
      await rootState.api.httpClient.autoSamplerImportBatch(data);
    },
    async createBatch({ rootState }, newBatch) {
      await rootState.api.httpClient.createBatch(newBatch);
    },
    async updateBatch({ rootState }, newBatch) {
      await rootState.api.httpClient.updateBatch(newBatch);
    },

    async deleteBatch({ dispatch, rootState }, batch) {
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "deleteBatch",
        requestData: batch,
        progressNotificationPayload: {
          action: "delete",
          type: "batch",
          message: `Deleting batch "${batch.sample_batch_name}", please wait`,
        },
      });
    },

    async copyBatch({ dispatch, rootState }, sampleBatchCopyData) {
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "copySampleBatch",
        requestData: sampleBatchCopyData,
        progressNotificationPayload: {
          action: "copy",
          type: "batch",
          message: `Copying batch "${sampleBatchCopyData.sample_batch_name}" to the workspace "${sampleBatchCopyData.workspace_name}", please wait`,
        },
      });
    },

    async batchExportPeakData({ dispatch, rootState }, sampleBatch) {
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "batchExportPeakData",
        requestData: sampleBatch,
        progressNotificationPayload: {
          action: "export",
          type: "peaks",
          message: `Exporting peak data for batch "${sampleBatch.sample_batch_name}", please wait.`,
        },
      });
    },

    async matchBatchesRematch({ rootState }, batches) {
      const formattedBatches = batches.map((batch) => ({
        sample_batch_id: batch.sample_batch_id,
        workspace_id: batch.workspace_id,
      }));
      const body = {
        sample_batches: formattedBatches,
      };
      await rootState.api.httpClient.matchBatchesRematch(body);
    },

    // backend notifications
    async onSampleBatchReload({ dispatch }) {
      await dispatch("reload");
    },

    // selection
    async batchToggle({ rootState, state, dispatch }, batch) {
      rootState.workspace.batches.forEach((row) => (row.selection = 0));
      const active_batch_id = state.active
        ? state.active.sample_batch_id
        : null;
      if (active_batch_id == batch.sample_batch_id) {
        dispatch("unload");
      } else {
        dispatch("load", batch.sample_batch_id);
        rootState.workspace.batches
          .filter((row) => row.sample_batch_id == batch.sample_batch_id)
          .forEach((row) => (row.selection = 2));
      }
    },
    // Sample selection toggling
    async sampleItemFocus({ dispatch, getters, state }, sampleItemFocused) {
      const sampleItemFocusedId = sampleItemFocused.sample_item_id;
      state.sampleItems
        .filter(
          (row) =>
            row.sample_item_id != sampleItemFocusedId && row.selection == 3
        )
        .forEach((item) => (item.selection = 0));
      sampleItemFocused = getters["sampleItem"](sampleItemFocusedId);
      switch (sampleItemFocused.selection) {
        case 0:
        case 2:
          // Focus
          sampleItemFocused.selection = 3;
          await dispatch("sample/load", sampleItemFocused, { root: true });
          break;
        case 3:
          // Unfocus
          sampleItemFocused.selection = 0;
          await dispatch("sample/unload", null, { root: true });
          break;
      }
    },
    async sampleItemToggle({ getters, state }, sampleItemToggled) {
      const sampleItemToggledId = sampleItemToggled.sample_item_id;
      state.sampleItems
        .filter(
          (row) =>
            row.sample_item_id != sampleItemToggledId && row.selection == 2
        )
        .forEach((item) => (item.selection = 0));
      sampleItemToggled = getters["sampleItem"](sampleItemToggledId);
      switch (sampleItemToggled.selection) {
        case 0:
          // Select
          sampleItemToggled.selection = 2;
          break;
        case 2:
          // Unselect
          sampleItemToggled.selection = 0;
          break;
        case 3:
          // Stay focused
          sampleItemToggled.selection = 3;
          break;
      }
    },
    // target collection selection toggling
    async targetCollectionToggle(
      { commit, getters, state, dispatch, rootGetters },
      targetCollectionToggled
    ) {
      const targetCollectionToggledId =
        targetCollectionToggled.target_collection_id;
      state.targetCollections
        .filter(
          (row) =>
            row.target_collection_id != targetCollectionToggledId &&
            row.selection == 2
        )
        .forEach((collection) => (collection.selection = 0));
      targetCollectionToggled = getters["targetCollection"](
        targetCollectionToggledId
      );
      switch (targetCollectionToggled.selection) {
        case 0:
          commit("SET_COLLECTION_SELECTION", {
            collectionId: targetCollectionToggledId,
            selectionValue: 2,
          });
          break;
        case 2:
          // Unselect
          commit("SET_COLLECTION_SELECTION", {
            collectionId: targetCollectionToggledId,
            selectionValue: 0,
          });
          break;
        case 3:
          // Stay focused
          commit("SET_COLLECTION_SELECTION", {
            collectionId: targetCollectionToggledId,
            selectionValue: 3,
          });
          break;
      }
      // Dispatch to targets module to update selection there as well
      dispatch(
        "targets/updateCollectionSelection",
        {
          collectionId: targetCollectionToggledId,
          selectionValue: targetCollectionToggled.selection,
        },
        { root: true }
      );
      // Dispatch to sample module if sample is active to update selection there as well
      if (rootGetters["sample/matchCollections"].length > 0) {
        dispatch(
          "sample/updateCollectionSelection",
          {
            collectionId: targetCollectionToggledId,
            selectionValue: targetCollectionToggled.selection,
          },
          { root: true }
        );
      }
    },
  },
  getters: {
    buildParams: (state) => {
      return {
        calibration_collection: state.paramCalibrationCollection,
        ion_mechanisms: state.paramIonMechanisms,
      };
    },
    // get all rows as proxy array
    sampleItems: (state) => {
      return state.sampleItems ? state.sampleItems : [];
    },
    targetCollections: (state) => {
      return state.targetCollections ? state.targetCollections : [];
    },
    targetCompounds: (state) => {
      return state.targetCompounds ? state.targetCompounds : [];
    },
    targetIons: (state) => {
      return state.targetIons ? state.targetIons : [];
    },
    targetIsotopes: (state) => {
      return state.targetIsotopes ? state.targetIsotopes : [];
    },
    // get row from id
    sampleItem: (state, getters) => (sampleItemId) => {
      const [sampleItem] = getters["sampleItems"].filter(
        (row) => row.sample_item_id == sampleItemId
      );
      return sampleItem ?? null;
    },
    targetCollection: (state, getters) => (targetCollectionId) => {
      const [targetCollection] = getters["targetCollections"].filter(
        (row) => row.target_collection_id == targetCollectionId
      );
      return targetCollection ?? null;
    },
    targetCompound: (state, getters) => (targetCompoundId) => {
      const [targetCompound] = getters["targetCompounds"].filter(
        (row) => row.target_compound_id == targetCompoundId
      );
      return targetCompound ?? null;
    },
    targetIon: (state, getters) => (targetIonId) => {
      const [targetIon] = getters["targetIons"].filter(
        (row) => row.target_ion_id == targetIonId
      );
      return targetIon ?? null;
    },
    targetIsotope: (state, getters) => (targetIsotopeId) => {
      const [targetIsotope] = getters["targetIsotopes"].filter(
        (row) => row.target_isotope_id == targetIsotopeId
      );
      return targetIsotope ?? null;
    },
    // get selected
    sampleItemsSelected: (state, getters) => {
      return getters["sampleItems"].filter(
        (sampleItem) => sampleItem.selection >= 2
      );
    },
    sampleItemFocused: (state, getters) => {
      const sampleItem = getters["sampleItems"].filter(
        (sampleItem) => sampleItem.selection == 3
      );
      return sampleItem[0] ?? null;
    },
    targetCollectionsSelected: (state, getters) => {
      return getters["targetCollections"].filter((row) => row.selection >= 2);
    },
    targetCompoundsSelected: (state, getters) => {
      return getters["targetCompounds"].filter((row) => row.selection >= 2);
    },
    targetIonsSelected: (state, getters) => {
      return getters["targetIonsSelected"].filter((row) => row.selection >= 2);
    },
    targetIsotopesSelected: (state, getters) => {
      return getters["targetIsotopes"].filter((row) => row.selection >= 2);
    },
  },
};
