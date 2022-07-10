<template>
  <div>
    <the-modal-target-collection-op></the-modal-target-collection-op>
    <the-modal-workspace-save></the-modal-workspace-save>
    <the-modal-sample-batch-op></the-modal-sample-batch-op>
    <the-modal-sample-file-attributes-save></the-modal-sample-file-attributes-save>
    <the-modal-sample-item-attributes-save></the-modal-sample-item-attributes-save>
  </div>
</template>

<script>
import TheModalTargetCollectionOp from "./TheModalTargetCollectionOp.vue";
import TheModalWorkspaceSave from "./TheModalWorkspaceSave.vue";
import TheModalSampleBatchOp from "./TheModalSampleBatchOp.vue";
import TheModalSampleFileAttributesSave from "./TheModalSampleFileAttributesSave.vue";
import TheModalSampleItemAttributesSave from "./TheModalSampleItemAttributesSave.vue";

export default {
  name: "TheModalAggregator",
  components: {
    TheModalTargetCollectionOp,
    TheModalWorkspaceSave,
    TheModalSampleBatchOp,
    TheModalSampleFileAttributesSave,
    TheModalSampleItemAttributesSave,
  },
};
</script>
