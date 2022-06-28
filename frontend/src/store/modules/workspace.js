import { createTableModule } from "$lib/store";

export default createTableModule({
    namespace: 'workspace',
    children: [
        'sample/batch',
        'target/collection',
    ],
    loadWhen: 'always',
    singleSelect: true,
})