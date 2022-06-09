import schema from "./schema";
import stat from "./stat";

import { createTableModule } from "$lib/store";

export default createTableModule({
    parents: ['sample/batch'],
    namespace: 'sample/item',
    loadWhen: 'parent-selected',
    modules: {
        schema,
        stat
    }
});