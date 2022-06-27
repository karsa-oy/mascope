import { createTableModule } from "$lib/store";
import stat from "./stat";
import param from "./param";

export default {
    namespaced: true,
    modules: {
        collection: createTableModule({
            parents: ['sample/batch'],
            namespace: 'target/collection',
            children: ['target/compound'],
            loadWhen: 'parent-selected',
            singleSelect: true,
        }),
        compound: createTableModule({
            parents: ['target/collection'],
            namespace: 'target/compound',
            children: ['target/ion'],
        }),
        ion: createTableModule({
            parents: ['target/compound'],
            namespace: 'target/ion',
            children: ['target/isotope'],
            focusable: true,
        }),
        isotope: createTableModule({
            parents: ['target/ion'],
            namespace: 'target/isotope',
            params: {
                minIsotopeAbundance: 'target/param/minIsoAbu'
            }
        }),
        stat,
        param
    }
}