<template>
  <section style="padding: 1em">
    <h2 class="subtitle">Connection</h2>
    <b-field label="URL">
      <b-input v-model="apiUrl" lazy> </b-input>
    </b-field>
  </section>
</template>

<script>
import { mapState } from "vuex";

export default {
  name: "ThePaneSettingsConnection",
  computed: {
    ...mapState(["apiConnected"]),
    apiUrl: {
      get() {
        return this.$store.state.apiUrl;
      },
      set(value) {
        this.$store.commit("apiSetUrl", { url: value });
      },
    },
  },
};
</script>
