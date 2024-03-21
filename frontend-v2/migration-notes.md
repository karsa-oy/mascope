## Store

The stores are migrated to Pinia, with the 'setup store' model:

https://pinia.vuejs.org/core-concepts/#Setup-Stores

This means:

- **State** becomes `refs`
- **Actions** become functions
- **Getters** become `computed` values, and getters with parameters
  should return the function, i.e. `computed(() => (foo, bar) => baz)`.
- **Mutations** become either manual state changes, or custom functions
  which don't get exported from the store.

## Components

Components are migrated to the composition API with `<script setup>`:

https://vuejs.org/api/sfc-script-setup.html

In addition, the SFCs are reorganized to have `<script>` first, then
`<template>` and finally `<style>`. This is inline with conventions
in Vue and other frameworks.
