import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Role = "executive" | "sales_manager" | "category_manager" | "regional_manager";

export interface GlobalFilters {
  month: string | null;
  state: string | null;
  category: string | null;
  segment: string | null;
}

interface AppState {
  currentRole: Role;
  setRole: (role: Role) => void;
  
  // Unified Global Filters
  filters: GlobalFilters;
  setFilter: (key: keyof GlobalFilters, value: string | null) => void;
  resetFilters: () => void;
  
  // UI State
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

const initialFilters: GlobalFilters = {
  month: null,
  state: null,
  category: null,
  segment: null,
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentRole: "executive",
      setRole: (role) => set({ currentRole: role }),
      
      filters: { ...initialFilters },
      setFilter: (key, value) => 
        set((state) => ({ filters: { ...state.filters, [key]: value } })),
      resetFilters: () => set({ filters: { ...initialFilters } }),
      
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
    }),
    {
      name: "analytica-state",
      partialize: (state) => ({
        currentRole: state.currentRole,
        filters: state.filters,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
      merge: (persisted: unknown, current: AppState) => {
        const p = persisted as Record<string, any>;
        const storedFilters = p?.filters ? { ...p.filters } : {};
        delete storedFilters.seller;
        return {
          ...current,
          ...p,
          filters: { ...current.filters, ...storedFilters },
        };
      },
    }
  )
);
