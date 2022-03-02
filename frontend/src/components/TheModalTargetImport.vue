<template>
  <section>
    <b-modal
      :active.sync="modalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
    >
      <div class="columns">
        <div class="modal-card" style="height: 85vh">
          <header class="modal-card-head">
            <p class="modal-card-title">Import from Excel clipboard</p>
          </header>
          <section class="modal-card-body">
            <b-field label="Ionization mechanisms">
              <b-taginput
                v-model="ionMechs"
                ellipsis
                icon="label"
                placeholder="Add ionization mechanisms"
                aria-close-label="Delete ionization mechanism"
              >
              </b-taginput>
            </b-field>
            <b-field label="Target compounds">
              <template v-if="cols.length > 1 && rows.length > 0">
                <section>
                  <section
                    style="
                      font-style: italic;
                      color: #b7b7b7;
                      padding-bottom: 0.5em;
                    "
                  >
                    Paste spreadsheet data again with control + v to replace
                    targets
                  </section>
                  <section>
                    <b-table
                      :columns="cols"
                      :data="rows"
                      style="padding-bottom: 0.5em"
                    >
                    </b-table>
                  </section>
                </section>
              </template>
              <b-message v-else type="is-info" has-icon>
                Copy spreadsheet cells containing <i>target names</i> and
                <i>target formulae</i> with control + c and paste them here with
                control + v.
              </b-message>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button expanded @click="modalActive = false"> Cancel </b-button>
            <b-button type="is-primary" expanded @click="saveTargets()">
              Import
            </b-button>
          </footer>
        </div>
      </div>
    </b-modal>
  </section>
</template>

<script>
import { bindState } from "$lib/store";

import { mapActions } from "vuex";

import table from "$lib/table";

export default {
  name: "",
  components: {},
  props: {},
  computed: {
    ...bindState({
      ionMechs: "workspace/target/ionMechs",
      defaultIonMechs: "workspace/target/defaultIonMechs",
      modalActive: "ui/modal/targetImportActive",
      control: "ui/key/control",
      v: "ui/key/v",
    }),
    fields() {
      return this.cols.map((col) => col.field);
    },
  },
  data: function () {
    return {
      clipboardText: "",
      rows: [],
      cols: [
        { field: "name", label: "Name" },
        { field: "formula", label: "Formula" },
      ],
    };
  },
  created() {
    this.ionMechs = this.defaultIonMechs;
  },
  destroyed() {
    this.rows = [];
  },
  methods: {
    ...mapActions({
      addTargets: "workspace/target/add",
    }),
    parseClipboard: async function () {
      let clipboardText = await navigator.clipboard.readText();
      this.rows = table.fromSpreadsheet(clipboardText, this.fields);
    },
    saveTargets: function () {
      this.addTargets({ compounds: this.rows });
      this.modalActive = false;
    },
  },
  watch: {
    control: function () {
      if (this.control && this.v && this.modalActive) {
        this.parseClipboard();
      }
    },
    v: function () {
      if (this.control && this.v && this.modalActive) {
        this.parseClipboard();
      }
    },
  },
};
</script>