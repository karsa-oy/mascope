<template>
  <div>
    <the-modal-target-import></the-modal-target-import>
    <the-modal-workspace-save></the-modal-workspace-save>
  </div>
</template>

<script>
import TheModalTargetImport from "./TheModalTargetImport";
import TheModalWorkspaceSave from "./TheModalWorkspaceSave";

export default {
  name: "TheModalAggregator",
  components: {
    TheModalTargetImport,
    TheModalWorkspaceSave,
  },
};
</script>