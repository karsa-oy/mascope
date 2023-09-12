import { dispatch, make } from "vuex-pathify";
import { camelToSnakeCase } from "../../lib/util";

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
  // filter parameters
  paramIsotopeRatioTolerance: null,
  paramMinIsotopeAbundance: null,
  paramMinIsotopeCorrelation: null,
  paramMzTolerance: null,
  paramPeakMinIntensity: null,
  paramPeakMinSeparation: null,
  paramPossibleMatchThreshold: null,
  paramProbableMatchThreshold: null,
};

const paramDefaults = {
  // build parameters
  paramCalibrationCollection: [],
  paramIonMechanisms: [],
  // filter parameters
  paramIsotopeRatioTolerance: 0.1,
  paramMinIsotopeAbundance: 0.15,
  paramMinIsotopeCorrelation: 0.8,
  paramMzTolerance: 15,
  paramPeakMinIntensity: 0,
  paramPeakMinSeparation: null,
  paramPossibleMatchThreshold: 0.7,
  paramProbableMatchThreshold: 0.8,
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
    async load({ rootState, state, commit, dispatch }, batch) {
      if (state.active) await dispatch("unload");
      rootState.api.emit("subscribe", batch.sample_batch_id);
      await commit("SET_ACTIVE", batch);
      await dispatch("unpackParams");
      await dispatch("loadBatchTargets");
      await dispatch("loadBatch");
    },

    async loadBatch(
      { rootState, state, commit, getters },
      sampleItemIdActive = null
    ) {
      const batchId = state.active.sample_batch_id;
      const filterParams = getters["filterParams"];
      const reqBody = {
        sample_batch_id: batchId,
        batch_matches_info: true,
        filter_params: { ...filterParams },
        sort: "datetime_utc",
        order: "asc",
      };

      // Add the sample_item_id_active if provided
      if (sampleItemIdActive) {
        reqBody.sample_item_id_active = sampleItemIdActive;
      }

      try {
        const response = await rootState.api.httpClient.getAllSamples(reqBody);
        if (response.data) {
          response.data.data.forEach(
            (row, i) => (row.index = (i + 1).toString())
          );
          commit("SET_SAMPLE_ITEMS", response.data.data);
          if (!response.data.batch_matches_info) return;
          commit(
            "SET_MATCH_SAMPLES",
            response.data.batch_matches_info.match_samples
          );
          commit(
            "SET_MATCH_COMPOUNDS",
            response.data.batch_matches_info.match_compounds
          );
          commit("SET_MATCH_IONS", response.data.batch_matches_info.match_ions);
        }
      } catch (error) {
        console.error("Failed to load batch data: ", error);
      }
    },

    async loadBatchTargets({ rootState, rootGetters, state, commit }) {
      const batchId = state.active.sample_batch_id;
      const ionMechanisms = state.active.build_params.ion_mechanisms;

      const body = {
        sample_batch_id: batchId,
        ion_mechanisms: ionMechanisms,
      };
      try {
        const response = await rootState.api.httpClient.loadBatchTargets(body);

        if (response && response.data) {
          const data = response.data.data;

          let targetCollections = data.target_collections;

          const activeCollection = rootGetters["targets/activeCollection"];
          if (targetCollections) {
            targetCollections = targetCollections.map((coll) => {
              if (
                activeCollection &&
                activeCollection.target_collection_id ===
                  coll.target_collection_id
              ) {
                coll.selection = 2;
              } else {
                coll.selection = 0;
              }
              return coll;
            });
          }

          commit("SET_TARGET_COLLECTIONS", targetCollections);
          commit("SET_TARGET_COMPOUNDS", data.target_compounds);
          commit("SET_TARGET_IONS", data.target_ions);
          commit("SET_TARGET_ISOTOPES", data.target_isotopes);
        }
      } catch (error) {
        console.error("Failed to load batch targets: ", error);
      }
    },

    async reload(
      { rootGetters, getters, rootState, state, dispatch, commit },
      batch = null
    ) {
      const batchToLoad = batch ? batch : state.active;
      if (batchToLoad) {
        const batchToLoadId = batchToLoad.sample_batch_id;
        const activeSample = rootState.sample.active;
        await dispatch("unload", false);
        const activeBatch = rootGetters["workspace/sampleBatch"](batchToLoadId);
        await dispatch("load", activeBatch);
        if (activeSample) {
          const sample = getters["sampleItem"](activeSample.sample_item_id);
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
      const filterParams = state.active.filter_params;
      for (const param in filterParams) {
        await commit(`SET_PARAM_${param.toUpperCase()}`, filterParams[param]);
      }
    },

    // backend notifications
    async onSampleBatchReload({ dispatch }) {
      await dispatch("reload");
    },

    // backend event emitters
    async reloadBatchInfo({ rootState }, sample_batch_id) {
      await rootState.api.httpClient.reloadBatch(sample_batch_id);
    },
    async matchBatchesCompute({ rootState }, sample_batches) {
      const formattedBatches = sample_batches.map((batch) => ({
        sample_batch_id: batch.sample_batch_id,
        workspace_id: batch.workspace_id,
      }));
      await rootState.api.httpClient.matchBatchesCompute(formattedBatches);
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
        dispatch("load", batch);
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
    filterParams: (state) => {
      return {
        isotope_ratio_tolerance: state.paramIsotopeRatioTolerance,
        min_isotope_abundance: state.paramMinIsotopeAbundance,
        min_isotope_correlation: state.paramMinIsotopeCorrelation,
        mz_tolerance: state.paramMzTolerance,
        peak_min_intensity: state.paramPeakMinIntensity,
        peak_min_separation: state.paramPeakMinSeparation,
        possible_match_threshold: state.paramPossibleMatchThreshold,
        probable_match_threshold: state.paramProbableMatchThreshold,
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
