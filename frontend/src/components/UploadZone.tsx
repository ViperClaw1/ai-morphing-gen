"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { useProjectStore } from "@/store/projectStore";

const ACCEPTED_MIME_TYPES = { "image/jpeg": [], "image/png": [], "image/webp": [] };
const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024; // ponytail: fixed constant, promote to env/config if a real limit lands server-side
const MAX_FILES = 10;

function rejectionMessage(rejection: FileRejection): string {
  const code = rejection.errors[0]?.code;
  if (code === "file-too-large") return `${rejection.file.name}: over 15MB`;
  if (code === "file-invalid-type") return `${rejection.file.name}: unsupported file type`;
  if (code === "too-many-files") return `${rejection.file.name}: too many files`;
  return `${rejection.file.name}: ${rejection.errors[0]?.message ?? "rejected"}`;
}

export function UploadZone() {
  const assets = useProjectStore((s) => s.assets);
  const addAssets = useProjectStore((s) => s.addAssets);
  const [rejections, setRejections] = useState<string[]>([]);

  const onDrop = useCallback(
    (accepted: File[], fileRejections: FileRejection[]) => {
      setRejections(fileRejections.map(rejectionMessage));
      if (accepted.length > 0) addAssets(accepted);
    },
    [addAssets],
  );

  const remainingSlots = Math.max(0, MAX_FILES - assets.length);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_MIME_TYPES,
    maxSize: MAX_FILE_SIZE_BYTES,
    maxFiles: remainingSlots,
    disabled: remainingSlots === 0,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        data-testid="upload-zone"
        className={`flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          isDragActive ? "border-foreground bg-foreground/5" : "border-foreground/20"
        } ${remainingSlots === 0 ? "cursor-not-allowed opacity-50" : ""}`}
      >
        <input {...getInputProps()} aria-label="Upload face photos" />
        {remainingSlots === 0 ? (
          <p className="text-sm text-foreground/60">Maximum {MAX_FILES} photos reached</p>
        ) : isDragActive ? (
          <p className="text-sm">Drop photos here</p>
        ) : (
          <p className="text-sm text-foreground/60">
            Drag &amp; drop face photos here, or click to select ({remainingSlots} remaining, JPEG/PNG/WebP, max 15MB
            each)
          </p>
        )}
      </div>
      {rejections.length > 0 && (
        <ul role="alert" className="mt-2 space-y-1 text-sm text-red-600">
          {rejections.map((message, i) => (
            <li key={i}>{message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
