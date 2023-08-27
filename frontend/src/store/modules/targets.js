import { make } from "vuex-pathify";

const state = {
  activeCollection: null,
  targetCollectionsAll: [],
  targetCompoundsAll: [],
};

export default {
  namespaced: true,
  state,
  mutations: {
    ...make.mutations(state),
    SET_COLLECTION_ALL_SELECTION: (state, { collectionId, selectionValue }) => {
      const collection = state.targetCollectionsAll.find(
        (coll) => coll.target_collection_id === collectionId
      );
      if (collection) {
        collection.selection = selectionValue;
      }
    },
    SET_ACTIVE_COLLECTION: (state, collection) => {
      state.activeCollection = collection;
    },
  },
  actions: {
    async load({ rootState, state, commit, dispatch }, batch) {
      await dispatch("loadAllCollections");
      await dispatch("loadAllCompounds");
    },

    async loadAllCollections({ commit, rootState }) {
      try {
        const response =
          await rootState.api.httpClient.getAllTargetCollections();
        if (response && response.data) {
          const collections = response.data.data.map((collection) => {
            return { ...collection, selection: 0 };
          });
          await commit("SET_TARGET_COLLECTIONS_ALL", collections);
        }
      } catch (error) {
        console.error("Failed to load target collections: ", error);
      }
    },

    async loadAllCompounds({ commit, rootState }, collectionId) {
      try {
        const response = await rootState.api.httpClient.getAllTargetCompounds({
          collectionId,
        });
        if (response && response.data) {
          await commit("SET_TARGET_COMPOUNDS_ALL", response.data.data);
        }
      } catch (error) {
        console.error("Failed to load target compounds: ", error);
      }
    },

    async setActiveCollection({ commit }, collection) {
      await commit("SET_ACTIVE_COLLECTION", collection);
    },

    async unload({ rootState, commit, dispatch }) {
      await commit("SET_ACTIVE_COLLECTION", null);
      await commit("SET_TARGET_COLLECTIONS_ALL", []);
      await commit("SET_TARGET_COMPOUNDS_ALL", []);
    },

    async updateCollectionSelection(
      { commit, state, getters, rootState },
      { collectionId, selectionValue }
    ) {
      // Only one collection can be selected at a time
      state.targetCollectionsAll
        .filter(
          (coll) =>
            coll.target_collection_id !== collectionId && coll.selection === 2
        )
        .forEach((coll) => (coll.selection = 0));

      // Update the selected collection's selection value
      commit("SET_COLLECTION_ALL_SELECTION", {
        collectionId,
        selectionValue,
      });

      // If a collection is selected, fetch its details
      const selectedCollections = getters.targetCollectionsSelected;
      if (selectionValue === 2 && selectedCollections.length === 1) {
        const response = await rootState.api.httpClient.getTargetCollectionById(
          collectionId
        );
        if (response && response.data) {
          commit("SET_ACTIVE_COLLECTION", response.data);
        }
      } else {
        commit("SET_ACTIVE_COLLECTION", null);
      }
    },
  },

  getters: {
    getCollectionById: (state) => (collectionId) => {
      return (
        state.targetCollectionsAll.find((coll) => coll.id === collectionId) ||
        null
      );
    },
    getCompoundById: (state) => (compoundId) => {
      return (
        state.targetCompoundsAll.find((comp) => comp.id === compoundId) || null
      );
    },
    // get selected
    targetCollectionsSelected: (state) => {
      return state.targetCollectionsAll.filter((row) => row.selection >= 2);
    },
  },
};
