<template>
  <b-field :label="label">
    <template v-if="cols.length > 1 && rows.length > 0">
      <section>
        <section
          style="font-style: italic; color: #b7b7b7; padding-bottom: 0.5em"
        >
          Paste spreadsheet data again to replace data.
        </section>
        <section>
          <b-table :columns="cols" :data="rows" style="padding-bottom: 0.5em">
          </b-table>
        </section>
      </section>
    </template>
    <b-message v-else type="is-info" has-icon>{{ info }}</b-message>
  </b-field>
</template>

<script>
import table from "$lib/table";
import { get } from "vuex-pathify";

export default {
  name: "BaseSpreadsheetInput",
  props: {
    label: {
      type: String,
      required: true,
    },
    cols: {
      type: Array,
      required: true,
    },
    info: {
      type: String,
      required: false,
      default: "Paste spreadsheet cells here",
    },
  },
  data: function () {
    return {
      clipboardText: "",
      rows: [],
    };
  },
  computed: {
    ...get({
      control: "key/control",
      v: "key/v",
    }),
    fields() {
      return this.cols.map((col) => col.field);
    },
  },
  methods: {
    parseClipboard: async function () {
      navigator.permissions.query({ name: "clipboard-read" });
      let clipboardText = await navigator.clipboard.readText();
      this.rows = table.fromSpreadsheet(clipboardText, this.fields);
      this.$emit("rowsPasted", this.rows);
    },
  },
  watch: {
    control: function () {
      if (this.control && this.v) {
        this.parseClipboard();
      }
    },
    v: function () {
      if (this.control && this.v) {
        this.parseClipboard();
      }
    },
  },
};
</script>
