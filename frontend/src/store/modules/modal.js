export default {
    namespaced: true,
    state: {
        // active modal indicator
        active: null,
        // modal-specific active sync helpers and data
        targetCollectionOpActive: false,
        targetCollectionOpProps: {

        },
        workspaceSaveActive: false,
        workspaceSaveProps: {
            // action ('create', 'edit' or 'delete')
            // workspaceId (required for edit or delete)
        },
        sampleBatchOpActive: false,
        sampleBatchOpProps: {
            // action ('create', 'edit' or 'delete')
            // workspaceId (required for edit or delete)
        },
        sampleFileAttributesSaveActive: false,
        sampleFileAttributesSaveProps: {
            // action ('create', 'edit' or 'delete')
            // sampleFileId (required for edit or delete)
        },
        sampleItemAttributesSaveActive: false,
        sampleItemAttributesSaveProps: {
            // action ('create', 'edit' or 'delete')
            // sampleItemId (required for edit or delete)
        },
    },
    mutations: {
        activate(state, { modal }) {
            state.active = modal;
            state[modal + 'Active'] = true;
        },
        deactivate(state) {
            for (let activeState in state) {
                state[activeState] = false;
            }
            state.active = null;
        }
    }
}