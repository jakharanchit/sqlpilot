// src/store/clientStore.ts
import { create } from "zustand";
import type { ClientSummary } from "@/types/index";

interface ClientStore {
  activeClient: string;
  clients: ClientSummary[];

  setActiveClient:  (name: string)           => void;
  setClients:       (clients: ClientSummary[]) => void;
}

export const useClientStore = create<ClientStore>((set) => ({
  activeClient: "",
  clients:      [],

  setActiveClient: (name)    => set({ activeClient: name }),
  setClients:      (clients) => set({ clients }),
}));
