"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Card } from "@/components/ui";

interface UploadedFile {
  id: string;
  file: File;
  progress: number;
  status: "pending" | "uploading" | "completed" | "error";
  fileId?: string;
  error?: string;
}

interface FileUploadProps {
  onFilesUploaded: (fileIds: string[]) => void;
  jobId?: string;
}

export function FileUpload({ onFilesUploaded, jobId }: FileUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";
  const authToken = process.env.NEXT_PUBLIC_API_AUTH_TOKEN;
  const [assignedJobId, setAssignedJobId] = useState<string | undefined>(jobId);

  useEffect(() => {
    setAssignedJobId(jobId);
  }, [jobId]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleFiles = async (newFiles: File[]) => {
    const uploadedFiles: UploadedFile[] = newFiles.map((file) => ({
      id: Math.random().toString(36).substring(7),
      file,
      progress: 0,
      status: "pending" as const,
    }));

    setFiles((prev) => [...prev, ...uploadedFiles]);

    // Upload sequentially so we can reuse job IDs once created
    const successfulFileIds: string[] = [];
    let activeJobId = assignedJobId;

    for (const uploadFile of uploadedFiles) {
      const result = await uploadSingleFile(uploadFile, activeJobId);

      if (result?.jobId) {
        activeJobId = result.jobId;
        setAssignedJobId(result.jobId);
      }

      if (result?.fileId) {
        successfulFileIds.push(result.fileId);
      }
    }

    if (successfulFileIds.length > 0) {
      onFilesUploaded(successfulFileIds);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      handleFiles(selectedFiles);
    }
  };

  const uploadSingleFile = async (
    uploadFile: UploadedFile,
    targetJobId?: string
  ): Promise<{ fileId: string; jobId?: string } | null> => {
    const formData = new FormData();
    formData.append("file", uploadFile.file);
    if (targetJobId) {
      formData.append("job_id", targetJobId);
    }

    const headers: HeadersInit = {};
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }

    let progressInterval: NodeJS.Timeout | null = null;

    try {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id ? { ...f, status: "uploading", progress: 0 } : f
        )
      );

      // Simulate progress for UX
      progressInterval = setInterval(() => {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id && f.progress < 90
              ? { ...f, progress: f.progress + 10 }
              : f
          )
        );
      }, 200);

      const response = await fetch(`${apiBaseUrl}/api/files/upload`, {
        method: "POST",
        body: formData,
        headers,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed (${response.status}): ${errorText || response.statusText}`);
      }

      const result = await response.json();
      console.log("Upload response:", result);
      const resolvedJobId = result.job_id || targetJobId;
      const fileId = result.id as string;

      console.log("Resolved job_id:", resolvedJobId, "fileId:", fileId);

      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: "completed", progress: 100, fileId }
            : f
        )
      );

      return { fileId, jobId: resolvedJobId };
    } catch (error) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: "error",
                error: error instanceof Error ? error.message : "Upload failed",
              }
            : f
        )
      );
      return null;
    } finally {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
    }
  };

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl transition-all duration-300
          ${
            isDragging
              ? "border-fluent-blue-500 bg-fluent-blue-500/10"
              : "border-dark-border hover:border-fluent-blue-400/50"
          }
        `}
      >
        <div className="p-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-fluent-blue-500/20">
            <svg
              className="h-8 w-8 text-fluent-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          <p className="mb-2 text-sm font-medium text-dark-text-primary">
            Drop files here or click to browse
          </p>
          <p className="text-xs text-dark-text-tertiary">
            Supports logs, configs, traces, and documentation files
          </p>
          <input
            type="file"
            multiple
            onChange={handleFileInput}
            className="absolute inset-0 cursor-pointer opacity-0"
            accept=".log,.txt,.json,.yaml,.yml,.xml,.conf,.cfg,.trace,.md"
            aria-label="Upload files for analysis"
          />
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <Card className="p-4">
          <h3 className="section-title mb-3">Uploaded Files ({files.length})</h3>
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-3 rounded-lg bg-dark-bg-tertiary/60 p-3 transition-all hover:bg-dark-bg-tertiary"
              >
                {/* File Icon */}
                <div className="flex-shrink-0">
                  {file.status === "completed" && (
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-fluent-success/20">
                      <svg
                        className="h-4 w-4 text-green-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                  )}
                  {file.status === "error" && (
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-fluent-error/20">
                      <svg
                        className="h-4 w-4 text-red-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </div>
                  )}
                  {(file.status === "pending" || file.status === "uploading") && (
                    <div className="flex h-8 w-8 items-center justify-center">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-fluent-blue-500 border-t-transparent" />
                    </div>
                  )}
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-dark-text-primary">
                    {file.file.name}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-dark-text-tertiary">
                    <span>{formatFileSize(file.file.size)}</span>
                    {file.status === "uploading" && (
                      <span className="text-fluent-blue-400">Uploading... {file.progress}%</span>
                    )}
                    {file.status === "completed" && (
                      <span className="text-green-400">Uploaded</span>
                    )}
                    {file.status === "error" && (
                      <span className="text-red-400">{file.error}</span>
                    )}
                  </div>

                  {/* Progress Bar */}
                  {file.status === "uploading" && (
                    <UploadProgressBar progress={file.progress} />
                  )}
                </div>

                {/* Remove Button */}
                <button
                  onClick={() => removeFile(file.id)}
                  className="icon-button flex-shrink-0"
                  title="Remove file"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function UploadProgressBar({ progress }: { progress: number }) {
  const barRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (barRef.current) {
      const nextWidth = Math.min(Math.max(progress, 0), 100);
      barRef.current.style.width = `${nextWidth}%`;
    }
  }, [progress]);

  return (
    <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-dark-bg-primary">
      <div ref={barRef} className="h-full bg-fluent-blue-500 transition-all duration-300" />
    </div>
  );
}
