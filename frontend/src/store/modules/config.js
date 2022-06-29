import { createTableModule } from "$lib/store";

export default {
    namespaced: true,
    modules: {
        ion_mechanism: createTableModule({
            namespace: 'config/ion_mechanism',
        })
    }
}