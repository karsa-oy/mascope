import { make } from "vuex-pathify";
import { handleApiRequest, getApiData } from "./apiHelper";

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
    async load({ state, dispatch }, collectionId = null) {
      if (state.activeCollection) await dispatch("unload");
      await dispatch("loadAllCollections");
      await dispatch("loadAllCompounds");
      if (!collectionId) return;
      await dispatch("loadActiveCollection", collectionId);
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

    async loadActiveCollection({ commit, dispatch }, collectionId) {
      const collection = await dispatch("getTargetCollection", collectionId);
      await commit("SET_ACTIVE_COLLECTION", collection);
    },

    async reload({ dispatch, state, rootState }, collection = null) {
      const collectionToLoadId =
        state?.activeCollection?.target_collection_id || null;
      // const currentActiveCollection = state?.activeCollection || null;
      await dispatch("unload");
      await dispatch("load", collectionToLoadId);
      if (!collectionToLoadId) return;
      await dispatch("updateCollectionSelection", {
        collectionId: collectionToLoadId,
        selectionValue: 2,
      });
    },

    async unload({ commit }) {
      await commit("SET_TARGET_COLLECTIONS_ALL", null);
      await commit("SET_TARGET_COMPOUNDS_ALL", null);
      if (!state.activeCollection) return;
      await commit("SET_ACTIVE_COLLECTION", null);
    },

    processSpreadsheetInput({ state }, rows) {
      // process the spreadsheet input to check if compounds already exist
      let existingCompounds = [];
      let notExistingCompounds = [];
      let processedFormulas = new Set(); // Set to track processed compound formulas
      rows.forEach((row) => {
        // Skip processing if this formula has already been processed
        if (processedFormulas.has(row.target_compound_formula)) {
          return;
        }

        const existingCompound = state.targetCompoundsAll.find(
          (compound) =>
            compound.target_compound_formula === row.target_compound_formula
        );

        if (existingCompound) {
          //  If an existing compound is found, add it to existingCompounds
          existingCompounds.push(existingCompound);
        } else {
          // If no existing compound is found, add the row to notExistingCompounds
          notExistingCompounds.push(row);
        }

        // Mark this formula as processed
        processedFormulas.add(row.target_compound_formula);
      });
      return { existingCompounds, notExistingCompounds };
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

    async getAllTargetCompounds({ dispatch }, params = {}) {
      const compounds = await getApiData({
        dispatch,
        httpMethod: "getAllTargetCompounds",
        requestData: params,
        errorMessage: `Failed to load all target compounds.`,
      });
      return compounds.data;
    },

    async createCollection({ dispatch, rootState }, collection) {
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "createTargetCollection",
        requestData: collection,
        successMessage: `Target collection ${collection.target_collection_name} created successfully!`,
        errorMessage: `Failed to create target collection ${collection.target_collection_name}. Please try again.`,
      });
    },

    async updateCollection({ dispatch, rootState }, collection) {
      const collectionId = collection.target_collection_id;
      const body = collection;
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "updateTargetCollection",
        requestData: { collectionId, body },
        successMessage: `Target collection ${collection.target_collection_name} updated successfully!`,
        errorMessage: `Failed to update target collection ${body.target_collection_name}. Please try again.`,
      });
    },

    async deleteCollection(
      { commit, dispatch, rootState },
      { collectionId, collectionName, deleteOrphanCompounds }
    ) {
      await commit("SET_ACTIVE_COLLECTION", {});
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "deleteTargetCollection",
        requestData: { collectionId, collectionName, deleteOrphanCompounds },
        successNotificationType: "deleted",
        successMessage: `Target collection ${collectionName} was deleted successfully!`,
        errorMessage: `Failed to delete workspace ${collectionName}. Please try again.`,
      });
    },

    // backend notifications
    async onTargetsAllReload({ dispatch }) {
      dispatch("reload");
    },

    // selection
    async updateCollectionSelection(
      { commit, dispatch, state, getters },
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
        await dispatch("loadActiveCollection", collectionId);
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
    getAllCompounds: (state) => {
      return state?.targetCompoundsAll || [];
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
