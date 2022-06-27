import { createTableModule } from "$lib/store";

export default createTableModule({
    namespace: 'workspace',
    children: [
        'sample/batch'
    ],
    loadWhen: 'always',
    singleSelect: true,
})