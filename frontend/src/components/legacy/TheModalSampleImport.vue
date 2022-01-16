<template>
  <section class="sample-import-modal">
    <b-modal
      :active.sync="modalSampleImportActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
    >
      <div>
        <div class="modal-card" style="width: 500px; height: 700px">
          <header class="modal-card-head">
            <p class="modal-card-title">Import samples</p>
          </header>
          <section class="modal-card-body">
            <BaseImportSamples ref="sampleImport"></BaseImportSamples>
            <div><br /></div>
          </section>
          <footer class="modal-card-foot">
            <button
              class="button"
              type="button"
              @click="$refs.sampleImport.importSamples()"
              is-dark
              :disabled="false"
            >
              Import
            </button>
            <button
              class="button"
              type="button"
              is-dark
              @click="modalSampleImportActive = false"
            >
              Cancel
            </button>
          </footer>
        </div>
      </div>
    </b-modal>
  </section>
</template>