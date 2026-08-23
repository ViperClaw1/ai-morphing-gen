import { create } from "zustand";

export type AssetStatus = "pending" | "uploading" | "uploaded" | "error";

export interface ProjectAsset {
  clientId: string;
  file: File;
  previewUrl: string;
  status: AssetStatus;
  serverAssetId?: string;
  error?: string;
}

interface ProjectState {
  projectId: string | null;
  assets: ProjectAsset[];
  setProjectId: (id: string) => void;
  addAssets: (files: File[]) => void;
  removeAsset: (clientId: string) => void;
  reorderAssets: (fromIndex: number, toIndex: number) => void;
  updateAsset: (clientId: string, patch: Partial<ProjectAsset>) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projectId: null,
  assets: [],

  setProjectId: (id) => set({ projectId: id }),

  addAssets: (files) =>
    set((state) => ({
      assets: [
        ...state.assets,
        ...files.map((file) => ({
          clientId: crypto.randomUUID(),
          file,
          previewUrl: URL.createObjectURL(file),
          status: "pending" as const,
        })),
      ],
    })),

  removeAsset: (clientId) =>
    set((state) => {
      const target = state.assets.find((a) => a.clientId === clientId);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return { assets: state.assets.filter((a) => a.clientId !== clientId) };
    }),

  reorderAssets: (fromIndex, toIndex) =>
    set((state) => {
      const next = [...state.assets];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      return { assets: next };
    }),

  updateAsset: (clientId, patch) =>
    set((state) => ({
      assets: state.assets.map((a) => (a.clientId === clientId ? { ...a, ...patch } : a)),
    })),
}));
