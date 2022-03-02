<template>
  <section class="base-top-bar">
    <b-field grouped group-multiline>
      <div class="control">
        <b-taglist v-if="sampleTag" attached>
          <b-tag type="is-light"> sample {{ sampleTag.level }} </b-tag>
          <b-tag type="is-primary" aria-close-label="Close tag" closable>
            {{ sampleTag.label }}
          </b-tag>
        </b-taglist>
      </div>
      <div class="control">
        <b-taglist v-if="targetTag" attached>
          <b-tag type="is-light"> target {{ targetTag.level }} </b-tag>
          <b-tag type="is-info" aria-close-label="Close tag" closable>
            {{ targetTag.label }}
          </b-tag>
        </b-taglist>
      </div>
    </b-field>
  </section>
</template>

<script>
import { bindState } from "$lib/store";

export default {
  name: "ThePanelTopBar",
  components: {},
  computed: {
    ...bindState({
      sampleSelected: "ui/selected/sample",
      targetSelected: "ui/selected/target",
    }),
    sampleTag: function () {
      if (!this.sampleSelected.row) {
        return null;
      } else {
        let level = this.sampleSelected.level;
        let label;
        switch (level) {
          case "batch":
            label = this.sampleSelected.row.name;
            break;
          case "item":
            label = this.sampleSelected.row.filename;
            break;
          case "peak":
            label = "peak";
            break;
        }
        return { level, label };
      }
    },
    targetTag: function () {
      if (!this.targetSelected.row) {
        return null;
      } else {
        let level = this.targetSelected.level;
        let label;
        switch (level) {
          case "compound":
            label =
              this.targetSelected.row.name || this.targetSelected.row.formula;
            break;
          case "ion":
            label = this.targetSelected.row.formula;
            break;
          case "isotope":
            label = this.targetSelected.row.mz;
            break;
        }
        return { level, label };
      }
    },
  },
};
</script>

<style>
.base-top-bar {
  padding: 0.5em;
  display: flex;
  flex-flow: row-reverse nowrap;
}
</style>
