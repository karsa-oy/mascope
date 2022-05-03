<template>
  <the-layout-sidebar>

    <section style="padding: 2em 2em 2em 2em">
    <h1 class="title">Welcome to workspace {{workspaceActive.name}} !</h1>
    </section>
    <section style="padding: 2em 2em 2em 2em">
    <h1 class="title">Browse to other pages to get started</h1>
    </section>

  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from './TheLayoutSidebar';
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
