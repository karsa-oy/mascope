import createLogger from "vuex/dist/logger";

export default createLogger({
  filter(mutation) {
    return false;
  },
  actionFilter(action) {
    return !action.type.startsWith("key");
  },
});
