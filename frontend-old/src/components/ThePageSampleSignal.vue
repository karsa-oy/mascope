<template>
  <the-layout-sidebar>
    <section>
      <the-pane-sample-signal></the-pane-sample-signal>
    </section>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from './TheLayoutSidebar.vue'
import ThePaneSampleSignal from './ThePaneSampleSignal.vue'

export default {
  name: 'ThePageSampleSignal',
  components: {
    TheLayoutSidebar,
    ThePaneSampleSignal,
  },
}
</script>
