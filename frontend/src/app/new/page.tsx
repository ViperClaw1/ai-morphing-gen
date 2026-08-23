"use client";

import { useEffect, useRef } from "react";
import { UploadZone } from "@/components/UploadZone";
import { ImageSorter } from "@/components/ImageSorter";
import { Progress } from "@/components/ui/progress";
import { useProjectStore } from "@/store/projectStore";
import { createProject, uploadAsset, ApiError } from "@/lib/api";

export default function NewProjectPage() {
  const projectId = useProjectStore((s) => s.projectId);
  const setProjectId = useProjectStore((s) => s.setProjectId);
  const assets = useProjectStore((s) => s.assets);
  const updateAsset = useProjectStore((s) => s.updateAsset);
  const projectCreation = useRef<Promise<void> | null>(null);
  const dispatched = useRef(new Set<string>());

  useEffect(() => {
    if (projectId || projectCreation.current) return;
    projectCreation.current = createProject()
      .then((project) => setProjectId(project.id))
      .catch((err) => console.error("Failed to create project:", err));
  }, [projectId, setProjectId]);

  useEffect(() => {
    if (!projectId) return;
    for (const asset of assets) {
      if (asset.status !== "pending" || dispatched.current.has(asset.clientId)) continue;
      dispatched.current.add(asset.clientId);
      updateAsset(asset.clientId, { status: "uploading" });
      uploadAsset(projectId, asset.file)
        .then((res) => updateAsset(asset.clientId, { status: "uploaded", serverAssetId: res.id }))
        .catch((err) =>
          updateAsset(asset.clientId, {
            status: "error",
            error: err instanceof ApiError ? err.message : "Upload failed",
          }),
        );
    }
  }, [assets, projectId, updateAsset]);

  const uploadedCount = assets.filter((a) => a.status === "uploaded").length;

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 px-6 py-16">
      <div>
        <h1 className="font-mono text-2xl tracking-tight">New morph project</h1>
        <p className="text-sm text-foreground/60">
          Upload a sequence of face photos, then drag to set the order they&apos;ll morph through.
        </p>
      </div>

      <UploadZone />

      {assets.length > 0 && (
        <div className="space-y-1">
          <Progress value={(uploadedCount / assets.length) * 100} />
          <p className="text-xs text-foreground/60">
            {uploadedCount} / {assets.length} uploaded
          </p>
        </div>
      )}

      <ImageSorter />
    </div>
  );
}
