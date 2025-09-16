import axios from "axios";

import { apiClient } from "@/lib/api-client";

export type Project = {
  id: string;
  name: string;
  created_at: string;
};

export type VoiceProfile = {
  id: string;
  name: string;
  provider: string;
  provider_params: Record<string, unknown>;
};

export type AssetMeta = Record<string, unknown>;

export type AssetUploadRequest = {
  projectId: string;
  type: "video" | "image" | "text";
  filename: string;
  mime: string;
};

export type AssetUploadResponse = {
  asset_id: string;
  upload_url: string;
  object_key: string;
  fields: Record<string, string>;
};

export type JobOptions = {
  subs: boolean;
  dub: boolean;
  replace_text_in_frame: boolean;
  upload_to_youtube: boolean;
};

export type LocalizationVariant = {
  id: string;
  lang: string;
  status: string;
  video_url?: string;
  audio_url?: string;
  subs_url?: string;
  preview_url?: string;
  report?: Record<string, unknown> | null;
};

export type LocalizationJob = {
  id: string;
  project_id: string;
  status: string;
  source_asset_id: string;
  languages: string[];
  voice_profile_id?: string | null;
  options: JobOptions;
  created_at: string;
  updated_at: string;
  variants: LocalizationVariant[];
};

export async function fetchProjects(): Promise<Project[]> {
  const { data } = await apiClient.get<Project[]>("/projects");
  return data;
}

export async function createProject(name: string): Promise<Project> {
  const { data } = await apiClient.post<Project>("/projects", { name });
  return data;
}

export async function getProject(projectId: string): Promise<Project> {
  const { data } = await apiClient.get<Project>(`/projects/${projectId}`);
  return data;
}

export async function getVoiceProfiles(): Promise<VoiceProfile[]> {
  const { data } = await apiClient.get<VoiceProfile[]>("/voice-profiles");
  return data;
}

export async function createUploadUrl(payload: AssetUploadRequest): Promise<AssetUploadResponse> {
  const { data } = await apiClient.post<AssetUploadResponse>("/assets/upload-url", payload);
  return data;
}

export async function completeUpload(payload: {
  projectId: string;
  type: "video" | "image" | "text";
  s3_url: string;
  meta: AssetMeta;
}): Promise<string> {
  const { data } = await apiClient.post<{ id: string }>("/assets/complete", payload);
  return data.id;
}

export async function createJob(payload: {
  projectId: string;
  sourceAssetId: string;
  languages: string[];
  voiceProfileId?: string | null;
  options: JobOptions;
}): Promise<LocalizationJob> {
  const { data } = await apiClient.post<LocalizationJob>("/jobs", payload);
  return data;
}

export async function getJob(jobId: string): Promise<LocalizationJob> {
  const { data } = await apiClient.get<LocalizationJob>(`/jobs/${jobId}`);
  return data;
}

export function jobEventSource(jobId: string, token: string) {
  const url = new URL(`/jobs/${jobId}/stream`, process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080");
  url.searchParams.set("token", token);
  return new EventSource(url.toString());
}

export async function getVariantDownload(variantId: string) {
  const { data } = await apiClient.get<{ mp4: string | null; srt: string | null }>(`/variants/${variantId}/download`);
  return data;
}

export async function publishToYoutube(variantId: string, payload: { title: string; description: string; tags: string[] }) {
  const { data } = await apiClient.post<{ youtube_url: string }>("/youtube/upload", {
    variantId,
    ...payload,
  });
  return data.youtube_url;
}

export async function putObject(uploadUrl: string, file: File, mime: string) {
  await axios.put(uploadUrl, file, { headers: { "Content-Type": mime } });
}
