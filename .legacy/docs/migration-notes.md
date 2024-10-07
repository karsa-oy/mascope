# Overview

In March 2024, a migration was performed to upgrade the frontend
of Mascope to Vue 3.

tl;dr:

- A fresh project was setup with `npm create vue`
- The `pinia`, `eslint` and `prettier` options were selected
- This means `vue@3.4.21` and `pinia@2.1.7` were installed
- Store modules were moved one by one and converted to Pinia
  - Vuex pathify was replaced by standard Pinia features
- Components were moved one by one and converted:
  - Standard SFC format was used (script first and style last)
  - The new `<script setup>` form was leveraged
  - Store imports were updated to work with pinia
- Dependencies were reinstalled if they were used in the codebase
- `buefy` was exchanged for `@ntohq/buefy-next`

Note that `yarn` is not used in the new project. In 2024, there
are no real advantages to using `yarn` over `npm`. We could
consider `pnpm` for improved dependency management in the future.

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

Gotchas:

- You can't `watch` store paths directly. Instead watch a computed
  like so: `watch(computed(() => someStore.foo.bar), () => { doStuff() })`

## Components to Vue 3 w/ SFC Script Setup

Components are migrated to the composition API with `<script setup>`:

https://vuejs.org/api/sfc-script-setup.html

In addition, the SFCs are reorganized to have `<script>` first, then
`<template>` and finally `<style>`. This is inline with conventions
in Vue and other frameworks.

## Vue 3 syntax changes of note

- `:foo.sync="bar"` is now `v-model:foo="bar"`

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

When performing a clone of a `ref`, use `toRaw` (from Vue):

`const copy = structuredClone(toRaw(original))`

## Returning from short arrow functions

The following are equivalent:

```
const fooShort = () => "bar"
const fooLong = () => {
  return "bar"
}
```

In cases where we are returning a simple expression, the former is
preferable since its easier to read:

```
const fooShort = () => somethingTrue ? "yay" : "boo"
const fooLong = () => {
  return somethingTrue ? "yay" : "boo"
}
```

## Testing

Getting started with testing can be daunting. I wonder if a good
way to begin is with some like https://playwright.dev/.

In particular, it lets you autogenerate tests by clicking around
in the browser: https://playwright.dev/docs/codegen

This could be a way to take you tacit QA knowledge and encode it
in tests without considerable effort.

I haven't used it yet myself, but it is suggested by major
frameworks like Vite and Svelte when creating a new project, so
it must be quite solid.
