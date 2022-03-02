import createLogger from 'vuex/dist/logger';

export default createLogger({
    filter(mutation) {
        let hiddenMutationTypes = [
            'setPath',
            'key/activate',
            'key/deactivate',
            'target/selectionSet',
            'sample/selectionSet',
        ]
        return !hiddenMutationTypes
            .includes(mutation.type)
    },
})