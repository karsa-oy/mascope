import { make } from "vuex-pathify";
import { getApiData } from "./apiHelper";

const state = {
  activeCollection: null,
  // alarm_mode
  alarmTargets: true,
  alarmDiagnostics: false,
  alarmCalibrants: false,
  // all targets
  targetCollectionsAll: null,
  targetCompoundsAll: null,
};

// TODO_configuration possible collection types
const collectionTypes = ["TARGETS", "DIAGNOSTICS", "CALIBRANTS"];

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
  },
  actions: {
    // data loading
    async load({ state, dispatch }) {
      if (state.activeCollection) await dispatch("unload");
      await dispatch("loadAllCollections");
      await dispatch("loadAllCompounds");
    },

    async loadAllCollections({ commit, dispatch }) {
      let collections = await dispatch("getAllTargetCollections");

      collections = collections.map((collection) => {
        return { ...collection, selection: 0 };
      });

      await commit("SET_TARGET_COLLECTIONS_ALL", collections);
    },

    async loadAllCompounds({ commit, dispatch }) {
      const compounds = await dispatch("getAllTargetCompounds");
      await commit("SET_TARGET_COMPOUNDS_ALL", compounds);
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

    async unload({ commit }) {
      await commit("SET_TARGET_COLLECTIONS_ALL", null);
      await commit("SET_TARGET_COMPOUNDS_ALL", null);
      if (!state.activeCollection) return;
      await commit("SET_ACTIVE_COLLECTION", null);
    },

    // http client endpoints
    async getAllTargetCollections({ dispatch }) {
      const collections = await getApiData({
        dispatch,
        httpMethod: "getAllTargetCollections",
        errorMessage: `Failed to load all target collections.`,
      });
      return collections.data;
    },

    async getTargetCollection({ dispatch }, collectionId) {
      return await getApiData({
        dispatch,
        httpMethod: "getTargetCollection",
        requestData: collectionId,
        errorMessage: `Failed to get target collection.`,
      });
    },

    async getAllTargetCompounds({ dispatch }) {
      const compounds = await getApiData({
        dispatch,
        httpMethod: "getAllTargetCompounds",
        errorMessage: `Failed to load all target compounds.`,
      });
      return compounds.data;
    },

    async createCollection({ rootState }, newCollection) {
      await rootState.api.httpClient.createTargetCollection(newCollection);
    },

    async updateCollection({ rootState }, newCollection) {
      await rootState.api.httpClient.updateTargetCollection(newCollection);
    },

    async deleteCollection({ rootState }, collection) {
      await rootState.api.httpClient.deleteTargetCollection(collection);
    },

    async removeTargetCollectionsFromSampleBatch(
      { rootState },
      { collectionsToRemove, skipRematch = false }
    ) {
      await rootState.api.httpClient.removeTargetCollectionsFromSampleBatch(
        collectionsToRemove,
        skipRematch
      );
    },

    async addTargetCollectionToSampleBatch({ rootState }, addedCollections) {
      await rootState.api.httpClient.addTargetCollectionToSampleBatch(
        addedCollections
      );
    },

    // backend notifications
    async onTargetsAllReload({ dispatch }) {
      dispatch("reload");
    },

    // selection
    async updateCollectionSelection(
      { commit, dispatch, state, getters, rootState },
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
        const collection = await dispatch("getTargetCollection", collectionId);
        await commit("SET_ACTIVE_COLLECTION", collection);
      } else {
        commit("SET_ACTIVE_COLLECTION", null);
      }
    },
  },

  getters: {
    // get collections
    activeCollection: (state) => {
      return state.activeCollection ? state.activeCollection : null;
    },

    getAllCollections: (state) => {
      return state?.targetCollectionsAll || [];
    },
    getTargetsCollections: (state) => {
      return (
        state.targetCollectionsAll?.filter(
          (collection) => collection.target_collection_type === "TARGETS"
        ) || []
      );
    },
    getCalibrantsCollections: (state) => {
      return (
        state.targetCollectionsAll?.filter(
          (collection) => collection.target_collection_type === "CALIBRANTS"
        ) || []
      );
    },
    getDiagnosticsCollections: (state) => {
      return (
        state.targetCollectionsAll?.filter(
          (collection) => collection.target_collection_type === "DIAGNOSTICS"
        ) || []
      );
    },
    getCollection: (getters) => (targetCollectionId) => {
      const [targetCollection] = getters["getAllCollections"].filter(
        (row) => row.target_collection_id == targetCollectionId
      );
      return targetCollection ?? null;
    },
    collectionTypes: () => collectionTypes,
    // get alarm_mode list
    alarmsList: (state, getters) => {
      const alarmingTypes = [];
      for (const [key, value] of Object.entries(state)) {
        if (key.startsWith("alarm") && value) {
          const collectionType = key.replace("alarm", "").toUpperCase();
          if (getters.collectionTypes.includes(collectionType)) {
            alarmingTypes.push(collectionType);
          }
        }
      }
      return alarmingTypes;
    },
    // get selected
    targetCollectionsSelected: (state) => {
      return (
        state.targetCollectionsAll?.filter((row) => row.selection >= 2) || []
      );
    },
  },
};
