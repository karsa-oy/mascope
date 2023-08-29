<template>
  <the-layout>
    <div class="sidebar-page">
      <section class="sidebar-layout">
        <b-sidebar position="fixed" fullheight open reduce>
          <the-main-menu></the-main-menu>
        </b-sidebar>
        <div class="page-container">
          <div
            style="
              position: fixed;
              left: 6em;
              bottom: 3em;
              z-index: -1;
              width: 300px;
            "
          >
            <b-image
              :src="require('../assets/karsa_logo_white_rgb.png')"
              alt="Karsa Logo"
            ></b-image>
          </div>
          <slot></slot>
        </div>
      </section>
    </div>
  </the-layout>
</template>

<script>
import TheLayout from "./TheLayout.vue";
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
  background-color: #464752 !important;
}

.page-container {
  margin-left: 45px;
  padding: 1em;
  width: calc(100vw - 45px);
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.b-sidebar .sidebar-content.is-mini {
  width: 45px !important;
  overflow: hidden !important;
}
</style>
