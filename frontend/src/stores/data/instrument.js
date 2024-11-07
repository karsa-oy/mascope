import { defineModule } from "./lib/module";

import { api } from "@/api";

export const useInstrument = defineModule({
  name: "instrument",
  key: "instrument",
  subscribe: true,
  load: async () =>
    await api.http.get(`/instruments`, {
      use: "read",
      type: "load_instruments",
    }),
});
