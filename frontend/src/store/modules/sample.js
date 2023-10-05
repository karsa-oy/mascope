import { dispatch, make } from "vuex-pathify";

const state = {
  active: null,
  // matches
  matched: null,
  matchCollections: null,
  matchCompounds: null,
  matchIons: null,
  matchIsotopes: null,
};

export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    async load({ rootState, commit, dispatch }, sample) {
      // reset if previous sample loaded
      if (state.active) {
        dispatch("unload");
      }
      const sampleItemId = sample.sample_item_id;
      rootState.api.emit("subscribe", sampleItemId);
      // set sample active
      await commit("SET_ACTIVE", sample);
      await dispatch("loadMatches");
      await dispatch("calibration/load", sample, { root: true });
    },
    async loadMatches({ rootState, rootGetters, state, commit }) {
      const sampleItemId = state.active.sample_item_id;
      const filterParams = rootGetters["batch/filterParams"];

      // Check if matches exist for the given sampleItemId
      try {
        const response = await rootState.api.httpClient.getAllMatches({
          sample_item_id: sampleItemId,
        });
        commit("SET_MATCHED", response.data.data.length > 0 ? 1 : 0);
      } catch (error) {
        console.error("Failed to check for matches: ", error);
      }

      // Get detailed sample data
      try {
        const response = await rootState.api.httpClient.getSampleById(
          sampleItemId,
          filterParams
        );
        if (response && response.data) {
          let matchCollections = response.data.data.match_collections;

          const activeCollection = rootGetters["targets/activeCollection"];
          if (matchCollections) {
            matchCollections = matchCollections.map((coll) => {
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

          commit("SET_MATCH_COLLECTIONS", matchCollections);
          commit("SET_MATCH_COMPOUNDS", response.data.data.match_compounds);
          commit("SET_MATCH_IONS", response.data.data.match_ions);
          commit("SET_MATCH_ISOTOPES", response.data.data.match_isotopes);
        }
      } catch (error) {
        console.error("Failed to load matches: ", error);
      }
    },
    async unload({ rootState, state, commit, dispatch }) {
      if (!state.active) return;
      rootState.api.emit("unsubscribe", state.active.sample_item_id);
      commit("SET_ACTIVE", null);
      // matches
      commit("SET_MATCHED", null);
      commit("SET_MATCH_COLLECTIONS", null);
      commit("SET_MATCH_COMPOUNDS", null);
      commit("SET_MATCH_IONS", null);
      commit("SET_MATCH_ISOTOPES", null);
      // calibration
      dispatch("calibration/unload", null, { root: true });
    },
    async reload({ rootGetters, dispatch, state }, sample = null) {
      const sampleToLoad = sample ? sample : state.active;
      if (sampleToLoad) {
        await dispatch("unload");
        await dispatch("load", sampleToLoad);
      }
    },
    async create({ rootState }, sample) {
      await rootState.api.httpClient.createSampleItem(sample);
    },
    async update({ rootState }, sample) {
      await rootState.api.httpClient.updateSampleItem(
        sample.sample_item_id,
        sample
      );
    },
    async updateCollectionSelection(
      { commit, state },
      { collectionId, selectionValue }
    ) {
      // Only one collection can be selected at a time
      state.matchCollections
        .filter(
          (coll) =>
            coll.target_collection_id !== collectionId && coll.selection === 2
        )
        .forEach((coll) => (coll.selection = 0));

      const collection = state.matchCollections.find(
        (coll) => coll.target_collection_id === collectionId
      );
      if (collection) {
        collection.selection = selectionValue;
      }
    },

    async matchItemCompute({ rootState }, sample) {
      await rootState.api.httpClient.matchItemCompute(sample);
    },

    // backend notifications
    async onSampleBatchExportPeaksFailed({ dispatch }, error) {
      await dispatch(
        "app/pushNotification",
        { message: error, key: Math.random() },
        { root: true }
      );
    },
    async onSampleBatchExportPeaksReady({ dispatch }) {
      await dispatch(
        "app/pushNotification",
        { message: "Sample batch peak export finished", key: Math.random() },
        { root: true }
      );
    },
    async onSampleItemCreated({ rootGetters, dispatch }, sample_item_id) {
      await dispatch("batch/reload", null, { root: true });
      const sample_item = rootGetters["batch/sampleItem"](sample_item_id);
      await dispatch("load", sample_item);
    },
  },
  getters: {
    matchCollections: (state) => {
      return state.matchCollections ? state.matchCollections : [];
    },
  },
};
