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
    async load({ rootState, state, commit, dispatch }, collection_id = null) {
      if (state.activeCollection) await dispatch("unload");
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

    async reload({ dispatch, rootState }, collection = null) {
      const collectionToLoad = collection ? collection : state.activeCollection;
      if (collectionToLoad) {
        const collectionToLoadId = collectionToLoad.target_collection_id;
        await dispatch("unload");
        await dispatch("load");

        // Check if the collection is present in the batch's targetCollections before reselecting it
        const batchTargetCollections = rootState.batch.targetCollections;
        if (
          batchTargetCollections &&
          batchTargetCollections.some(
            (coll) => coll.target_collection_id === collectionToLoadId
          )
        ) {
          await dispatch("updateCollectionSelection", {
            collectionId: collectionToLoadId,
            selectionValue: 2,
          });
        }
      } else {
        // If no active collection, just refresh the list of collections without selecting any
        await dispatch("load");
      }
    },

    async unload({ rootState, commit, dispatch }) {
      await commit("SET_TARGET_COLLECTIONS_ALL", []);
      await commit("SET_TARGET_COMPOUNDS_ALL", []);
      if (!state.activeCollection) return;
      await commit("SET_ACTIVE_COLLECTION", null);
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
    // backend notifications
    async onTargetsAllReload({ dispatch }) {
      dispatch("reload");
    },
  },

  getters: {
    activeCollection: (state) => {
      return state.activeCollection ? state.activeCollection : null;
    },
    getTargetCollectionsAll: (state) => {
      return state.targetCollectionsAll ? state.targetCollectionsAll : [];
    },
    getTargetCollection: (state, getters) => (targetCollectionId) => {
      const [targetCollection] = getters["getTargetCollectionsAll"].filter(
        (row) => row.target_collection_id == targetCollectionId
      );
      return targetCollection ?? null;
    },
    // get selected
    targetCollectionsSelected: (state) => {
      return state.targetCollectionsAll.filter((row) => row.selection >= 2);
    },
  },
};
