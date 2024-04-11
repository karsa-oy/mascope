<script setup>
import TheLayoutMainView from './TheLayoutMainView.vue'

import ThePaneMainMenu from '@/components/panes/ThePaneMainMenu.vue'
</script>

<template>
  <the-layout-main-view>
    <div class="sidebar-page">
      <section class="sidebar-layout">
        <b-sidebar position="fixed" fullheight :modelValue="true" reduce>
          <the-pane-main-menu />
        </b-sidebar>
        <div class="page-container">
          <div style="position: fixed; left: 9em; bottom: 5em; z-index: -1; width: 200px">
            <b-image src="/karsa_logo_white_rgb.png" alt="Karsa Logo"></b-image>
          </div>
          <slot></slot>
        </div>
      </section>
    </div>
  </the-layout-main-view>
</template>

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
