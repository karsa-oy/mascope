<script setup>
import TheModalAggregator from '@/components/TheModalAggregator.vue'
import TheNotificationAggregator from '@/components/TheNotificationAggregator.vue'
</script>

<template>
  <div>
    <section>
      <the-modal-aggregator></the-modal-aggregator>
      <the-notification-aggregator></the-notification-aggregator>
      <slot></slot>
    </section>
  </div>
</template>
