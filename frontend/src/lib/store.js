export function bindState(bindings) {
    let computedBindings = Object.keys(bindings)
        .map((localVariable) => {
            let path = bindings[localVariable];
            return {
                [localVariable]: {
                    get() {
                        return this.$store.getters.getPath(path);
                    },
                    set(value) {
                        this.$store.commit('setPath', { path, value })
                    }
                }
            }
        });
    return Object.assign({}, ...computedBindings);
}