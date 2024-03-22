<template>
  <section>
    <section style="padding: 2em 2em 2em 2em">
      <h1 class="title is-4">{{ workspaceHomeText }}</h1>
    </section>
    <the-pane-browser-sample></the-pane-browser-sample>
    <div v-if="!sampleActive || sampleMatched">
      <!-- hide target browser if selected sample is not matched -->
      <the-pane-browser-target></the-pane-browser-target>
    </div>
  </section>
</template>

<script>
import ThePaneBrowserSample from './ThePaneBrowserSample.vue'
import ThePaneBrowserTarget from './ThePaneBrowserTarget.vue'

import { get } from 'vuex-pathify'

export default {
  name: 'ThePaneBrowser',
  components: {
    ThePaneBrowserTarget,
    ThePaneBrowserSample,
  },
  data: function () {
    return {}
  },
  computed: {
    ...get({
      batchActive: 'batch/active',
      sampleActive: 'sample/active',
      sampleMatched: 'sample/matched',
      workspaceActive: 'workspace/active',
    }),
    workspaceHomeText() {
      if (this.workspaceActive) {
        return `${this.workspaceActive.workspace_name}`
      } else {
        return `Loading workspace...`
      }
    },
  },
}
</script>
