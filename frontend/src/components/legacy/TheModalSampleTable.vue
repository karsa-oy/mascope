<template>
  <section class="sample-table-modal">
    <b-modal
      :active.sync="modalSampleTableActive"
      full-screen
      has-modal-card
      trap-focus
      :can-cancel="true"
      :destroy-on-hide="false"
      aria-role="dialog"
      aria-modal
    >
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">
            {{ $projectSelected.title }}: {{ $experimentSelected.title }}
          </p>
          <!-- Column visibility dropdown -->
          <b-dropdown
            aria-role="menu"
            type="is-dark"
            position="is-bottom-right"
            style="top: 0px"
            trap-focus
            multiple
            append-to-body
          >
            <b-button icon-left="menu" slot="trigger" type="is-dark">
            </b-button>
            <div>
              <div v-for="(col, i) in sampleTableCols" :key="i" class="control">
                <b-checkbox v-model="col.visible" size="is-small">
                  {{ col.label }}
                </b-checkbox>
              </div>
            </div>
          </b-dropdown>
          <!-- Close button -->
          <b-button
            icon-left="close"
            @click="modalSampleTableActive = false"
            type="is-dark"
          >
          </b-button>
        </header>

        <section class="modal-card-body">
          <!-- Sample table -->
          <b-table
            id="samples-datatable"
            :height="760"
            :data="sampleTableRows"
            :sticky-header="true"
            striped
          >
            <!-- Columns -->
            <b-table-column
              v-for="(col, i) in sampleTableCols"
              :key="i"
              :field="col.field"
              :label="col.label"
              searchable
              sortable
              :visible="col.visible === null ? true : col.visible"
              v-slot="props"
            >
              {{ props.row[col.field] }}
            </b-table-column>
            <!-- End of columns -->
          </b-table>
          <!-- End of sample table -->
        </section>
        <footer class="modal-card-foot">
          <b-button @click="exportSampleTable()"> Export CSV </b-button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>