import { create } from "zustand";
import { apiFetch, BACKEND_URL } from "../api/client";

export interface CaseListItem {
  id: string;
  title: string;
  description: string | null;
  patient_name: string | null;
  has_avatar: boolean;
  avatar_filename: string | null;
  avatar_url: string | null;
  scenario_type: string;
  status: "draft" | "published";
  creator_name: string | null;
  created_at: string;
  updated_at: string;
  /** When set, 2D practice uses these viseme PNGs under the Vite public folder */
  viseme_shapes_base_url?: string | null;
}

export interface CaseDetail extends CaseListItem {
  system_prompt: string;
  avatar_filename: string | null;
  avatar_url: string | null;
  voice_id: string | null;
  created_by: string;
}

export interface CaseCreatePayload {
  title: string;
  description?: string;
  system_prompt: string;
  patient_name?: string;
  has_avatar?: boolean;
  avatar_filename?: string;
  voice_id?: string;
  scenario_type?: string;
  status?: "draft" | "published";
}

async function uploadAvatarFile(token: string, caseId: string, file: File): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BACKEND_URL}/api/cases/${caseId}/avatar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Avatar upload failed" }));
    throw new Error(err.detail);
  }
}

interface CaseState {
  cases: CaseListItem[];
  isLoading: boolean;
  error: string | null;
  fetchCases: (token: string) => Promise<void>;
  createCase: (token: string, data: CaseCreatePayload, avatarFile?: File) => Promise<CaseDetail>;
  updateCase: (token: string, id: string, data: Partial<CaseCreatePayload>, avatarFile?: File) => Promise<CaseDetail>;
  deleteCase: (token: string, id: string) => Promise<void>;
  publishCase: (token: string, id: string) => Promise<void>;
  unpublishCase: (token: string, id: string) => Promise<void>;
}

export const useCaseStore = create<CaseState>((set, get) => ({
  cases: [],
  isLoading: false,
  error: null,

  fetchCases: async (token) => {
    set({ isLoading: true, error: null });
    try {
      const cases = await apiFetch<CaseListItem[]>("/cases", { token });
      set({ cases, isLoading: false });
    } catch (err: any) {
      set({ isLoading: false, error: err.message });
    }
  },

  createCase: async (token, data, avatarFile) => {
    const result = await apiFetch<CaseDetail>("/cases", {
      method: "POST",
      body: data,
      token,
    });
    // Upload avatar if provided
    if (avatarFile && data.has_avatar) {
      await uploadAvatarFile(token, result.id, avatarFile);
    }
    await get().fetchCases(token);
    return result;
  },

  updateCase: async (token, id, data, avatarFile) => {
    const result = await apiFetch<CaseDetail>(`/cases/${id}`, {
      method: "PATCH",
      body: data,
      token,
    });
    // Upload avatar if a new file was provided
    if (avatarFile) {
      await uploadAvatarFile(token, id, avatarFile);
    }
    await get().fetchCases(token);
    return result;
  },

  deleteCase: async (token, id) => {
    await apiFetch(`/cases/${id}`, { method: "DELETE", token });
    await get().fetchCases(token);
  },

  publishCase: async (token, id) => {
    await apiFetch(`/cases/${id}/publish`, { method: "POST", token });
    await get().fetchCases(token);
  },

  unpublishCase: async (token, id) => {
    await apiFetch(`/cases/${id}/unpublish`, { method: "POST", token });
    await get().fetchCases(token);
  },
}));
