<template>
  <section class="isotope-table-modal">
    <b-modal
      :active.sync="isModalIsotopeTableActive"
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
          <p class="modal-card-title"></p>
          <b-button
            icon-left="check"
            :type="isotopeTableShowOnlyChecked ? 'is-primary' : 'is-dark'"
            @click="isotopeTableShowOnlyChecked = !isotopeTableShowOnlyChecked"
          >
          </b-button>
          <!-- Column visibility dropdown -->
          <b-dropdown
            aria-role="menu"
            position="is-bottom-right"
            style="top: 0px"
            trap-focus
            multiple
            append-to-body
          >
            <b-button icon-left="menu" type="is-dark" slot="trigger">
            </b-button>
            <div>
              <div
                v-for="(col, i) in isotopeTableCols"
                :key="i"
                class="control"
              >
                <b-checkbox v-model="col.visible" size="is-small">
                  {{ col.label }}
                </b-checkbox>
              </div>
            </div>
          </b-dropdown>
          <!-- Close button -->
          <b-button
            icon-left="close"
            type="is-dark"
            @click="isModalIsotopeTableActive = false"
          >
          </b-button>
        </header>

        <section class="modal-card-body">
          <!-- Sample table -->
          <b-table
            id="samples-datatable"
            :height="760"
            :data="isotopeTableRows"
            :sticky-header="true"
            striped
          >
            <!-- Columns -->
            <b-table-column
              v-for="(col, i) in isotopeTableCols"
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
          <b-button @click="exportIsotopeTable()"> Export CSV </b-button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>