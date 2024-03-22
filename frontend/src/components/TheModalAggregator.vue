<script setup>
  import TheModalTargetCollectionOp from './TheModalTargetCollectionOp.vue'
  import TheModalWorkspaceSave from './TheModalWorkspaceSave.vue'
  import TheModalSampleBatchImport from './TheModalSampleBatchImport.vue'
  import TheModalSampleBatchOp from './TheModalSampleBatchOp.vue'
  import TheModalSampleItemAttributesSave from './TheModalSampleItemAttributesSave.vue'
  import TheModalSampleItemOverview from './TheModalSampleItemOverview.vue'
  import TheModalSampleItemTargetIon from './TheModalSampleItemTargetIon.vue'
</script>

<template>
  <div>
    <the-modal-target-collection-op></the-modal-target-collection-op>
    <the-modal-workspace-save></the-modal-workspace-save>
    <the-modal-sample-batch-import></the-modal-sample-batch-import>
    <the-modal-sample-batch-op></the-modal-sample-batch-op>
    <the-modal-sample-item-attributes-save></the-modal-sample-item-attributes-save>
    <the-modal-sample-item-overview></the-modal-sample-item-overview>
    <the-modal-sample-item-target-ion></the-modal-sample-item-target-ion>
  </div>
</template>