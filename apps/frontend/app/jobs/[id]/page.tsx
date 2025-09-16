"use client";

import { AlertTriangle, CheckCircle2, Loader2, Timer, XCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { getJob, jobEventSource, type LocalizationJob } from "@/lib/api";

const PIPELINE = ["asr", "translate", "tts", "mix", "subs", "textinframe", "qc", "pack"] as const;

type StageName = (typeof PIPELINE)[number];

type StageSnapshot = {
  status: string;
  progress: number;
  message?: string | null;
  timestamp: string;
};

type StageState = Record<StageName, StageSnapshot>;

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;
  const { token } = useAuth();
  const toast = useToast();
  const { data: job, mutate } = useSWR<LocalizationJob>(jobId ? ["job", jobId] : null, () => getJob(jobId));
  const [stageState, setStageState] = React.useState<Record<string, StageState>>({});
  const [waitAlert, setWaitAlert] = React.useState(false);

  React.useEffect(() => {
    if (!token || !jobId) return;
    const source = jobEventSource(jobId, token);
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          job_id: string;
          stage: StageName;
          status: string;
          progress?: number;
          message?: string;
          lang?: string | null;
          timestamp: string;
        };
        if (!payload.lang) {
          if (payload.stage === "job") {
            mutate();
          }
          return;
        }
        setStageState((prev) => {
          const stages = prev[payload.lang ?? "default"] ?? (PIPELINE.reduce((acc, stage) => {
            acc[stage] = { status: "queued", progress: 0, timestamp: payload.timestamp };
            return acc;
          }, {} as StageState));
          return {
            ...prev,
            [payload.lang ?? "default"]: {
              ...stages,
              [payload.stage]: {
                status: payload.status,
                progress: payload.progress ?? stages[payload.stage]?.progress ?? 0,
                message: payload.message,
                timestamp: payload.timestamp,
              },
            },
          };
        });
        if (payload.stage === "pack" && payload.status === "done") {
          toast({ title: `Variant ${payload.lang} ready`, description: "View results" });
          mutate();
        }
      } catch (error) {
        console.error("Failed to parse SSE", error);
      }
    };
    source.onerror = () => {
      source.close();
    };
    return () => {
      source.close();
    };
  }, [jobId, token, mutate, toast]);

  React.useEffect(() => {
    if (!job) return;
    const checkWait = () => {
      const created = new Date(job.created_at).getTime();
      const elapsedMinutes = (Date.now() - created) / (1000 * 60);
      setWaitAlert(elapsedMinutes >= 60 && job.status !== "done");
    };
    checkWait();
    const timer = window.setInterval(checkWait, 60_000);
    return () => window.clearInterval(timer);
  }, [job]);

  if (!job) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading job...
      </div>
    );
  }

  const languageStages = job.variants.map((variant) => ({
    lang: variant.lang,
    stages: stageState[variant.lang] ??
      PIPELINE.reduce((acc, stage) => {
        acc[stage] = {
          status: stage === "pack" && variant.status === "done" ? "done" : "queued",
          progress: 0,
          timestamp: job.updated_at,
        };
        return acc;
      }, {} as StageState),
  }));

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold">Job pipeline</h1>
          <p className="text-sm text-slate-400">Job ID: {job.id}</p>
          <p className="text-xs text-slate-500">Status: {job.status}</p>
        </div>
        <Button variant="outline" asChild>
          <Link href={`/results/${job.id}`}>View results</Link>
        </Button>
      </div>

      {waitAlert ? (
        <div className="flex items-center gap-4 rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-4 text-sm text-yellow-200">
          <AlertTriangle className="h-5 w-5" />
          <div>
            <p>This job has been running for over an hour.</p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2 border border-yellow-400/30 text-yellow-100"
              onClick={() => console.warn(`Support notified for job ${job.id}`)}
            >
              Notify support
            </Button>
          </div>
        </div>
      ) : null}

      <div className="grid gap-6">
        {languageStages.map(({ lang, stages }) => (
          <Card key={lang}>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <Badge>{lang}</Badge>
                <span className="text-sm font-normal text-slate-400">Variant pipeline</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {PIPELINE.map((stage) => {
                const snapshot = stages[stage];
                const icon = snapshot.status === "done" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : snapshot.status === "error" ? (
                  <XCircle className="h-4 w-4 text-red-400" />
                ) : snapshot.status === "processing" ? (
                  <Loader2 className="h-4 w-4 animate-spin text-brand" />
                ) : snapshot.status === "skipped" ? (
                  <Timer className="h-4 w-4 text-slate-400" />
                ) : (
                  <Loader2 className="h-4 w-4 text-slate-500" />
                );
                return (
                  <div key={stage} className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/40 px-4 py-3">
                    <div className="flex items-center gap-3">
                      {icon}
                      <div>
                        <p className="font-medium capitalize">{stage}</p>
                        {snapshot.message ? <p className="text-xs text-slate-400">{snapshot.message}</p> : null}
                      </div>
                    </div>
                    <div className="text-right text-xs text-slate-400">
                      <p>Status: {snapshot.status}</p>
                      <p>{new Date(snapshot.timestamp).toLocaleTimeString()}</p>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
