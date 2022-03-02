<template>
  <div>
    <the-modal-target-import></the-modal-target-import>
    <the-modal-workspace-save></the-modal-workspace-save>
    <the-modal-batch-save></the-modal-batch-save>
  </div>
</template>

<script>
import TheModalTargetImport from "./TheModalTargetImport";
import TheModalWorkspaceSave from "./TheModalWorkspaceSave";
import TheModalBatchSave from "./TheModalBatchSave";

export default {
  name: "TheModalAggregator",
  components: {
    TheModalTargetImport,
    TheModalWorkspaceSave,
    TheModalBatchSave,
  },
};
</script>