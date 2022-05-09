<template>
  <the-layout-sidebar>
    <section style="padding: 2em 2em 2em 2em">
      <h1 class="title is-3">
        Welcome to workspace {{ workspaceActive.name }}!
      </h1>
    </section>
    <section style="padding: 2em 2em 2em 2em">
      <h2 class="subtitle is-4">Browse to other pages to get started</h2>
    </section>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar";
import { bindState } from "$lib/store";

export default {
  name: "ThePageWorkspaceHome",
  components: {
    TheLayoutSidebar,
  },
  computed: {
    ...bindState({
      workspaceActive: "workspace/active",
    }),
  },
};
</script>
