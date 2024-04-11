<script setup>
import TheLayoutSidebarView from './TheLayoutSidebarView.vue'

import ThePaneAcquisitions from '@/components/panes/ThePaneAcquisitions.vue'
import ThePaneWorkspaces from '@/components/panes/ThePaneWorkspaces.vue'
</script>

<template>
  <the-layout-sidebar-view>
    <div class="columns">
      <div class="column is-half">
        <the-pane-acquisitions />
      </div>
      <div class="column is-half">
        <the-pane-workspaces />
      </div>
    </div>
  </the-layout-sidebar-view>
</template>
