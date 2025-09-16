"use client";

import Hls from "hls.js";
import * as React from "react";

export function HlsPlayer({ src, poster }: { src: string; poster?: string }) {
  const videoRef = React.useRef<HTMLVideoElement | null>(null);

  React.useEffect(() => {
    if (!src || !videoRef.current) return;
    if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
      videoRef.current.src = src;
    } else if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(videoRef.current);
      return () => {
        hls.destroy();
      };
    }
  }, [src]);

  return (
    <video ref={videoRef} controls poster={poster} className="w-full rounded-lg border border-slate-800" />
  );
}
