<template>
  <section class="raw-import-status-modal">
    <b-modal
      :active.sync="isRawImportStatusModalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
    >
      <div class="columns">
        <div class="modal-card" style="width: auto; height: 700px">
          <header class="modal-card-head">
            <p class="modal-card-title">
              Status of {{ dataSourceSelected.name }} Import...
            </p>
            <button
              class="button"
              type="button"
              @click="onButtonAcquisitionStatus()"
            >
              Refresh
            </button>
          </header>
          <section class="modal-card-body">
            <b-table
              :data="rawImportStatusRows"
              :columns="rawImportStatusCols"
              :checkable="true"
              :checked-rows.sync="rawImportStatusCheckedRows"
              :striped="true"
              :narrowed="true"
              :hoverable="true"
              draggable
              @dragstart="DragStart"
              @drop="DragDrop"
              @dragover="DragOver"
              @dragleave="DragLeave"
            >
            </b-table>
          </section>
          <footer class="modal-card-foot">
            <b-tooltip
              label="Import samples by modified import list"
              position="is-right"
            >
              <button
                class="button"
                type="button"
                @click="
                  importRawTableCheckedRows = rawImportStatusRows;
                  isRawImportStatusModalActive = false;
                  importSamples();
                "
                :disabled="isRawImportDataModified ? false : true"
              >
                ReImport
              </button>
              <div />
            </b-tooltip>
            <button
              class="button"
              type="button"
              @click="
                rawImportStatusCheckedRows = [];
                isRawImportStatusModalActive = false;
              "
            >
              Cancel
            </button>
            <div style="position: absolute; right: 20px">
              <b-tooltip
                label="Remove selected items from import list"
                position="is-left"
              >
                <b-button
                  type="is-dark"
                  icon-left="delete"
                  :disabled="
                    rawImportStatusCheckedRows.length == 0 ? true : false
                  "
                  @click="removeCheckedRows()"
                >
                </b-button>
              </b-tooltip>
            </div>
          </footer>
        </div>
      </div>
    </b-modal>
  </section>
</template>