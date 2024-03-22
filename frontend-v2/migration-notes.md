# Framework Upgrades

## Store to Pinia

The stores are migrated to Pinia, with the 'setup store' model:

https://pinia.vuejs.org/core-concepts/#Setup-Stores

This means:

- **State** becomes `refs`
- **Actions** become functions
- **Getters** become `computed` values, and getters with parameters
  should return the function, i.e. `computed(() => (foo, bar) => baz)`.
- **Mutations** become either manual state changes, or custom functions
  which don't get exported from the store.

Migrating from `vuex-pathify` proved easy: Pinia naturally facilitates
to store paths, and the standard notations of the library make it easy
to figure out how to migrate naything.

## Components to Vue 3 w/ SFC Script Setup

Components are migrated to the composition API with `<script setup>`:

https://vuejs.org/api/sfc-script-setup.html

In addition, the SFCs are reorganized to have `<script>` first, then
`<template>` and finally `<style>`. This is inline with conventions
in Vue and other frameworks.

## Near-Future Refactoring Suggestions

I've skipped some quick and easy refactoring ideas in the interest of
expediency. I suggest we do some cleanup soon:

- Use `reactive` over `ref` when possible to simplify state management

# Architecture & Code Style Notes

## Data Validation

It seems the application needs to deal with a lot of complex data
validation. We may benefit from using a library to do the heavy lifting
and help us architect these validation flows cleanly.

See `TheModalSampleBatchImport.vue` for an example of this challenge.

## Type safety

I've come to appreciate TypeScript since the last time I worked on the
codebase. It offers many advantages, including devtools that make it
easier to write code, compile-time validation to help catch bugs earlier
and better readability for code in general.

Migration to typescript can be incremental, since types are optional.

Typescript may also help with the data validation issue mentioned earlier.

## Defaults with ?? rather than ||

In modern JS, we have the nullish coalescing operator `??` for falling
back on default values. The `||` operator will cause issues when using
falsey values like `0` or `false` as intended values.

## structuredClone

There is a newish javascript standard function `structuredClone`. Our
code base has some uses of underscore's implementation of deep clones,
as well has hacky custom implementations. I replace instances of these
wherever I spot them.
