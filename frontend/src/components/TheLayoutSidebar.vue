<template>
  <the-layout>
    <div class="sidebar-page">
      <section class="sidebar-layout">
        <b-sidebar position="fixed" fullheight open reduce>
          <the-main-menu></the-main-menu>
        </b-sidebar>
        <div class="page-container">
          <slot></slot>
        </div>
      </section>
    </div>
  </the-layout>
</template>

<script>
import TheLayout from "./TheLayout";
import TheMainMenu from "./TheMainMenu.vue";

export default {
  name: "TheLayoutSidebar",
  components: {
    TheLayout,
    TheMainMenu,
  },
};
</script>

<style>
.sidebar-content {
  background-color: #29282e !important;
}

.page-container {
  margin-left: 45px;
  padding: 1em;
  width: calc(100vw - 45px);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.b-sidebar .sidebar-content.is-mini {
  width: 45px !important;
  overflow: hidden !important;
}
</style>