import { dispatch, make } from "vuex-pathify";
import { handleApiRequest, getApiData } from "./apiHelper";

const state = {
  active: null,
  // matches
  matched: null,
  matchCollections: null,
  matchCompounds: null,
  matchIons: null,
  matchIsotopes: null,
};

// TODO_configuration possible collection types
const sampleTypes = [
  "FILTER_REGENERATION",
  "FILTER_BACKGROUND",
  "INSTRUMENT_BACKGROUND",
  "BLANK",
  "SAMPLE",
  "UNKNOWN",
  "ONLINE", // At the moment not selectable from the UI
];

export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    // data loading
    async load({ rootState, commit, dispatch }, sample) {
      // reset if previous sample loaded
      if (state.active) await dispatch("unload");
      const sampleItemId = sample.sample_item_id;
      rootState.api.emit("subscribe", sampleItemId);
      // set sample active
      await commit("SET_ACTIVE", sample);
      await dispatch("loadSampleData", sampleItemId);
      await dispatch("calibration/load", sample, { root: true });
    },

    async loadSampleData({ rootGetters, commit, dispatch }, sampleItemId) {
      // Check if matches exist for the given sampleItemId
      const sampleMatches = await dispatch("getSampleMatches", sampleItemId);
      commit("SET_MATCHED", sampleMatches.length > 0 ? 1 : 0);

      // Get detailed sample data
      const sampleData = await dispatch("getSampleData", sampleItemId);

      // Set the selection of the active collection
      let matchCollections = sampleData.match_collections;
      const activeCollection = rootGetters["targets/activeCollection"];
      if (matchCollections) {
        matchCollections = matchCollections.map((coll) => {
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
      commit("SET_MATCH_COLLECTIONS", matchCollections);
      commit("SET_MATCH_COMPOUNDS", sampleData.match_compounds);
      commit("SET_MATCH_IONS", sampleData.match_ions);
      commit("SET_MATCH_ISOTOPES", sampleData.match_isotopes);
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

    async reload({ dispatch, state }, sample = null) {
      const sampleToLoad = sample ? sample : state.active;
      if (sampleToLoad) {
        await dispatch("unload");
        await dispatch("load", sampleToLoad);
      }
    },

    // http client endpoints
    async getSampleData({ rootGetters, dispatch }, sampleId) {
      const alarmsList = rootGetters["targets/alarmsList"];

      const body = {
        alarms_list: alarmsList,
      };

      const sampleData = await getApiData({
        dispatch,
        httpMethod: "getSample",
        requestData: {
          sampleId,
          body,
        },
        errorMessage: `Failed to load the sample data.`,
      });
      return sampleData.data;
    },

    async getSampleMatches({ dispatch }, sampleItemId) {
      const sampleMatches = await getApiData({
        dispatch,
        httpMethod: "getAllMatches",
        requestData: {
          sample_item_id: sampleItemId,
        },
        errorMessage: `Failed to check for matches of the sample.`,
      });
      return sampleMatches.data;
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
    async deleteSampleItem({ rootState }, sampleItemId) {
      await rootState.api.httpClient.deleteSampleItem(sampleItemId);
    },
    async matchSampleCompute({ rootState }, sample) {
      const sampleId = sample.sample_item_id;
      await rootState.api.httpClient.matchSampleCompute({ sampleId });
    },
    async matchSampleRematch({ rootState }, sample) {
      const sampleId = sample.sample_item_id;
      await rootState.api.httpClient.matchSampleRematch({ sampleId });
    },

    async copySample({ dispatch, rootState }, sample) {
      const sampleId = sample.sample_item_id;
      const body = {
        sample_batch_id: sample.sample_batch_id,
        sample_item_name: sample.sample_item_name,
      };
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "copySampleItem",
        requestData: { sampleId, body },
        progressNotificationPayload: {
          action: "copy",
          type: "sample",
          message: `Copying sample "${body.sample_item_name}" to "${body.workspace_name}/${body.sample_batch_name}", please wait`,
        },
      });
    },

    // Attribute templates
    async createAttributeTemplate({ dispatch, rootState }, newTemplate) {
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "createAttributeTemplate",
        requestData: newTemplate,
        successMessage: `Attribute template "${newTemplate.name}" created successfully!`,
        errorMessage: `Failed to create attribute template "${newTemplate.name}". Please try again.`,
      });
    },

    async updateAttributeTemplate({ dispatch, rootState }, template) {
      const templateId = template.attribute_template_id;
      const body = template;
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "updateAttributeTemplate",
        requestData: { templateId, body },
        successMessage: `Attribute template "${updateData.name}" updated successfully!`,
        errorMessage: `Failed to update attribute template "${updateData.name}". Please try again.`,
      });
    },

    async deleteAttributeTemplate({ dispatch, rootState }, template) {
      const templateId = template.attribute_template_id;
      const templateName = template.name;
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "deleteAttributeTemplate",
        requestData: { templateId, templateName },
        successNotificationType: "deleted",
        successMessage: `Attribute template "${templateName}" was deleted successfully!`,
        errorMessage: `Failed to delete attribute template ${templateName}. Please try again.`,
      });
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

    // selection
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
  },
  getters: {
    sampleTypes: () => sampleTypes,
    alarmCategory: (state, getters, rootGetters) => {
      if (!(state.matchCollections && state.matchCompounds)) return null;
      // Get ids of target collections set to alarm
      const alarmCollectionIds = getters["matchCollections"]
        .filter((collection) => collection.target_collection_type === "TARGETS")
        .map((collection) => collection.target_collection_id);
      // Get ids of target compounds set to alarm (based on belonging to alarming collection)
      const targetCompounds = rootGetters["batch"]["targetCompounds"];
      if (!targetCompounds) return null;
      const alarmCompoundIds = targetCompounds
        .filter((compound) =>
          alarmCollectionIds.includes(compound.target_collection_id)
        )
        .map((compound) => compound.target_compound_id);
      // Get match compound data for alarming compounds
      const alarmCompoundMatches = state.matchCompounds.filter((match) =>
        alarmCompoundIds.includes(match.target_compound_id)
      );
      // Return highest match category of alarming compounds
      return getters["maxMatchCategory"](alarmCompoundMatches);
    },
    matchCollections: (state) => {
      return state.matchCollections ? state.matchCollections : [];
    },
    maxMatchCategory:
      (state) =>
      (compounds = null) => {
        if (compounds === null) compounds = state.matchCompounds;
        return compounds && compounds.length > 0
          ? Math.max(...compounds.map((compound) => compound.match_category))
          : null;
      },
  },
};
