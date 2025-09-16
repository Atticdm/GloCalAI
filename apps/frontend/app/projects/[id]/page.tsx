"use client";

import { Loader2, UploadCloud } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  completeUpload,
  createJob,
  createUploadUrl,
  getProject,
  getVoiceProfiles,
  putObject,
  type JobOptions,
  type Project,
  type VoiceProfile,
} from "@/lib/api";
import { SUPPORTED_LANGUAGES } from "@/lib/constants";

async function readVideoMeta(file: File): Promise<Record<string, unknown>> {
  return new Promise((resolve) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.src = URL.createObjectURL(file);
    video.onloadedmetadata = () => {
      resolve({
        name: file.name,
        size: file.size,
        duration: video.duration,
        width: video.videoWidth,
        height: video.videoHeight,
        mime: file.type,
      });
      URL.revokeObjectURL(video.src);
    };
    video.onerror = () => {
      resolve({ name: file.name, size: file.size, mime: file.type });
    };
  });
}

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const router = useRouter();
  const toast = useToast();
  const { token } = useAuth();
  const { data: project, isLoading } = useSWR<Project>(projectId ? ["project", projectId] : null, () => getProject(projectId));
  const { data: profiles } = useSWR<VoiceProfile[]>(token ? "voice-profiles" : null, getVoiceProfiles);
  const [assetId, setAssetId] = React.useState<string | null>(null);
  const [assetMeta, setAssetMeta] = React.useState<Record<string, unknown> | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [languages, setLanguages] = React.useState<string[]>(["es", "pt-BR"]);
  const [voiceProfileId, setVoiceProfileId] = React.useState<string | undefined>();
  const [options, setOptions] = React.useState<JobOptions>({
    subs: true,
    dub: true,
    replace_text_in_frame: true,
    upload_to_youtube: false,
  });
  const [creatingJob, setCreatingJob] = React.useState(false);

  React.useEffect(() => {
    if (!voiceProfileId && profiles && profiles.length > 0) {
      setVoiceProfileId(profiles[0].id);
    }
  }, [profiles, voiceProfileId]);

  const onFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setUploading(true);
      const uploadDetails = await createUploadUrl({
        projectId,
        type: "video",
        filename: file.name,
        mime: file.type,
      });
      await putObject(uploadDetails.upload_url, file, file.type);
      const meta = await readVideoMeta(file);
      const s3Url = `${process.env.NEXT_PUBLIC_MINIO_PUBLIC_URL ?? "http://localhost:9000"}/glocal-media/${uploadDetails.object_key}`;
      const createdId = await completeUpload({
        projectId,
        type: "video",
        s3_url: s3Url,
        meta,
      });
      setAssetId(createdId);
      setAssetMeta(meta);
      toast({ title: "Asset uploaded", description: file.name });
    } catch (error) {
      console.error(error);
      toast({ title: "Upload failed", description: "Check MinIO endpoint and retry" });
    } finally {
      setUploading(false);
    }
  };

  const toggleLanguage = (lang: string) => {
    setLanguages((prev) => (prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]));
  };

  const updateOption = (key: keyof JobOptions) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setOptions((prev) => ({ ...prev, [key]: event.target.checked }));
  };

  const submitJob = async () => {
    if (!assetId) {
      toast({ title: "Upload required", description: "Upload a source asset before launching a job" });
      return;
    }
    if (languages.length === 0) {
      toast({ title: "Select languages", description: "Choose at least one target language" });
      return;
    }
    try {
      setCreatingJob(true);
      const job = await createJob({
        projectId,
        sourceAssetId: assetId,
        languages,
        voiceProfileId: voiceProfileId ?? undefined,
        options,
      });
      toast({ title: "Job created", description: `Tracking ${job.id}` });
      router.push(`/jobs/${job.id}`);
    } catch (error) {
      console.error(error);
      toast({ title: "Failed to create job", description: "See console for details" });
    } finally {
      setCreatingJob(false);
    }
  };

  return (
    <div className="space-y-8">
      {isLoading || !project ? (
        <div className="flex min-h-[50vh] items-center justify-center text-slate-400">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading project...
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold">{project.name}</h1>
              <p className="text-sm text-slate-400">Project ID: {project.id}</p>
            </div>
            {assetId ? <Badge>Asset ready</Badge> : <Badge className="bg-slate-800 text-slate-400">Awaiting asset</Badge>}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Upload source video</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-10 text-center text-slate-400 hover:border-brand">
                <UploadCloud className="mb-3 h-8 w-8 text-brand" />
                <span className="text-sm">Drag & drop or click to select a video file</span>
                <Input type="file" accept="video/*" className="hidden" disabled={uploading} onChange={onFileChange} />
              </label>
              {assetMeta ? (
                <dl className="grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
                  {Object.entries(assetMeta).map(([key, value]) => (
                    <div key={key} className="flex justify-between rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2">
                      <span className="uppercase text-xs text-slate-500">{key}</span>
                      <span>{String(value)}</span>
                    </div>
                  ))}
                </dl>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Localization settings</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-6 md:grid-cols-2">
              <div className="space-y-3">
                <h2 className="text-lg font-semibold">Target languages</h2>
                <div className="grid gap-2">
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <label key={lang.value} className="flex items-center gap-3">
                      <Checkbox
                        checked={languages.includes(lang.value)}
                        onChange={() => toggleLanguage(lang.value)}
                      />
                      <span>{lang.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="voice-profile">Voice profile</Label>
                  <Select
                    id="voice-profile"
                    value={voiceProfileId ?? ""}
                    onChange={(event) => setVoiceProfileId(event.target.value || undefined)}
                  >
                    <option value="">Auto select</option>
                    {profiles?.map((profile) => (
                      <option key={profile.id} value={profile.id}>
                        {profile.name}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Options</Label>
                  <div className="space-y-2 text-sm">
                    <label className="flex items-center gap-3">
                      <Checkbox checked={options.dub} onChange={updateOption("dub")} />
                      <span>Generate localized dub</span>
                    </label>
                    <label className="flex items-center gap-3">
                      <Checkbox checked={options.subs} onChange={updateOption("subs")} />
                      <span>Create localized subtitles</span>
                    </label>
                    <label className="flex items-center gap-3">
                      <Checkbox
                        checked={options.replace_text_in_frame}
                        onChange={updateOption("replace_text_in_frame")}
                      />
                      <span>Overlay localized text in frame (beta)</span>
                    </label>
                    <label className="flex items-center gap-3">
                      <Checkbox checked={options.upload_to_youtube} onChange={updateOption("upload_to_youtube")} />
                      <span>Trigger YouTube upload after completion</span>
                    </label>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={submitJob} disabled={creatingJob}>
              {creatingJob ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Launch localization
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
