<template>
  <div>
    <the-modal-target-import></the-modal-target-import>
    <the-modal-workspace-save></the-modal-workspace-save>
    <the-modal-batch-save></the-modal-batch-save>
    <the-modal-sample-file-attributes-save></the-modal-sample-file-attributes-save>
  </div>
</template>

<script>
import TheModalTargetImport from "./TheModalTargetImport";
import TheModalWorkspaceSave from "./TheModalWorkspaceSave";
import TheModalBatchSave from "./TheModalBatchSave";
import TheModalSampleFileAttributesSave from "./TheModalSampleFileAttributesSave";

export default {
  name: "TheModalAggregator",
  components: {
    TheModalTargetImport,
    TheModalWorkspaceSave,
    TheModalBatchSave,
    TheModalSampleFileAttributesSave,
  },
};
</script>
    TheModalSampleFileAttributesSave