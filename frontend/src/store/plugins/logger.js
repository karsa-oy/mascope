import { createLogger } from 'vuex';

export default createLogger({
  filter(mutation) {
    return false;
  },
  actionFilter(action) {
    return !action.type.startsWith("key");
  },
});
