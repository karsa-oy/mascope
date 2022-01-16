<template>
  <section class="raw-import-modal">
    <b-modal
      :active.sync="isRawImportModalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
    >
      <div class="columns">
        <div class="modal-card" style="width: 500px; height: 700px">
          <header class="modal-card-head">
            <p class="modal-card-title">
              Import {{ dataSourceSelected.type }} files
            </p>
          </header>
          <section class="modal-card-body">
            <b-field label="Start">
              <b-datetimepicker
                v-model="importStartTime"
                placeholder="Start datetime"
                :timepicker="{ 'hour-format': '24' }"
                :min-datetime="importMinDatetime"
                :max-datetime="importMaxDatetime"
              >
              </b-datetimepicker>
            </b-field>
            <b-field label="End">
              <b-datetimepicker
                v-model="importEndTime"
                placeholder="End datetime"
                :timepicker="{ 'hour-format': '24' }"
                :min-datetime="importStartTime"
                :max-datetime="importMaxDatetime"
              >
              </b-datetimepicker>
            </b-field>
            <button
              class="button"
              type="button"
              @click="fetchSamples()"
              is-dark
              :disabled="
                instrumentStatus === 'notReady' ||
                importStartTime === null ||
                importEndTime === null
                  ? true
                  : false
              "
            >
              Fetch {{ dataSourceSelected.name }} list
            </button>
            <div><br /></div>
            <b-table
              id="raw-samples-table"
              :columns="importRawTableCols"
              :data="importRawTableRows"
              :checkable="true"
              :checked-rows.sync="importRawTableCheckedRows"
            >
            </b-table>
            <div><br /></div>
          </section>
          <footer class="modal-card-foot">
            <button
              class="button"
              type="button"
              @click="importSamples()"
              is-dark
              :disabled="
                !importRawTableCheckedRows.length ||
                importStartTime === null ||
                importEndTime === null
                  ? true
                  : false
              "
            >
              Import
            </button>
            <button
              class="button"
              type="button"
              is-dark
              @click="
                importRawTableCheckedRows = [];
                isRawImportModalActive = false;
              "
            >
              Cancel
            </button>
            <b-upload v-model="batchImportList" class="file-label" rounded>
              <span class="file-cta">
                <b-icon class="file-icon" icon="file-document-outline"></b-icon>
                <span class="file-label">Batch Import...</span>
              </span>
            </b-upload>
          </footer>
        </div>
      </div>
    </b-modal>
  </section>
</template>