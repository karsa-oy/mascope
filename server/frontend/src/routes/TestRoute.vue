<script setup>
// testing playground
// http://localhost:5173/test

// do NOT commit changes to this route

import { api } from '@/api'

api.http
  .get('/datasets', {
    headers: {
      use: 'read',
      type: 'load_datasets'
    }
  })
  .then(console.log)
</script>

<template>
  <main>
    <h1>Test Route</h1>
  </main>
</template>

<style scoped>
/** testing playground */
main {
  padding: 1rem;
  width: 100%;
}
</style>
