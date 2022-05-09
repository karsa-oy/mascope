import createLogger from 'vuex/dist/logger';

export default createLogger({
    filter(mutation) {
        let hiddenMutationTypes = [
            'setPath',
            'key/activate',
            'key/deactivate',
            'target/SET_SELECTION',
            'match/LOAD',
            'match/UNLOAD',
        ]
        return !hiddenMutationTypes
            .includes(mutation.type)
    },
})