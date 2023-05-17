import VuexPersistence from "vuex-persist";

export const sessionStorage = new VuexPersistence({
  storage: window.sessionStorage,
  modules: [], //['workspace', 'target', 'sample', 'match']
}).plugin;
