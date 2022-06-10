import { createTableModule } from "$lib/store";

export default createTableModule({
    parents: ['workspace'],
    namespace: 'sample/batch',
    children: ['sample/item', 'target/collection'],
    loadWhen: 'parent-selected',
    singleSelect: true
});