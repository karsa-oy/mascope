import { createTableModule } from "$lib/store";

export default createTableModule({
    namespace: 'workspace',
    children: [
        'target/collection',
        'sample/batch'
    ],
    singleSelect: true,
})