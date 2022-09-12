<template>
  <the-layout-sidebar>
    <div class="section" style="overflow-y: auto">
      <div
        class="container is-max-widescreen"
        style="padding-right: 5em; padding-left: 3em"
      >
        <h1 class="title">Settings</h1>
      </div>
    </div>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar.vue";

export default {
  name: "ThePageSettings",
  components: {
    TheLayoutSidebar,
  },
};
</script>
