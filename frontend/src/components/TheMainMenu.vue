<template>
  <base-menu-bar :buttons="buttons" :footerButtons="footerButtons">
  </base-menu-bar>
</template>

<script>
import BaseMenuBar from "./BaseMenuBar.vue";

export default {
  name: "TheMainMenu",
  components: {
    BaseMenuBar,
  },
  data: function () {
    return {
      buttons: [
        {
          icon: "flask",
          label: "Batch overview",
          path: "/batch-overview",
        },
      ],
      footerButtons: [
        {
          icon: "tune",
          label: "Settings",
          path: "/settings",
        },
        {
          icon: "logout-variant",
          label: "Change workspace",
          path: "/",
        },
      ],
    };
  },
};
</script>
