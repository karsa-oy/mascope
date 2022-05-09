<template>
  <the-layout-sidebar>
    <div class="section" style="overflow-y: auto">
      <div
        class="container is-max-widescreen"
        style="padding-right: 5em; padding-left: 3em"
      >
        <h1 class="title">Settings</h1>
        <the-pane-settings-match></the-pane-settings-match>
        <the-pane-settings-target></the-pane-settings-target>
        <the-pane-settings-connection></the-pane-settings-connection>
      </div>
    </div>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar";
import ThePaneSettingsConnection from "./ThePaneSettingsConnection";
import ThePaneSettingsMatch from "./ThePaneSettingsMatch";
import ThePaneSettingsTarget from "./ThePaneSettingsTarget";

export default {
  name: "ThePageSettings",
  components: {
    TheLayoutSidebar,
    ThePaneSettingsConnection,
    ThePaneSettingsMatch,
    ThePaneSettingsTarget,
  },
};
</script>
