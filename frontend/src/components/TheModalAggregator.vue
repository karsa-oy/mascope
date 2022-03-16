<template>
  <div>
    <the-modal-target-import></the-modal-target-import>
    <the-modal-workspace-save></the-modal-workspace-save>
    <the-modal-batch-save></the-modal-batch-save>
    <the-modal-update-store></the-modal-update-store>
  </div>
</template>

<script>
import TheModalTargetImport from "./TheModalTargetImport";
import TheModalWorkspaceSave from "./TheModalWorkspaceSave";
import TheModalBatchSave from "./TheModalBatchSave";
import TheModalUpdateStore from "./TheModalUpdateStore";

export default {
  name: "TheModalAggregator",
  components: {
    TheModalTargetImport,
    TheModalWorkspaceSave,
    TheModalBatchSave,
    TheModalUpdateStore,
  },
};
</script>