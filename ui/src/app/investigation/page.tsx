"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { FileUpload } from "@/components/investigation/FileUpload";
import { JobConfigForm } from "@/components/investigation/JobConfigForm";
import { StreamingChat } from "@/components/investigation/StreamingChat";
import { PlatformDetectionCard } from "@/components/jobs";
import { usePlatformDetection } from "@/hooks/usePlatformDetection";

export default function InvestigationPage() {
  const [uploadedFileIds, setUploadedFileIds] = useState<string[]>([]);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>("idle");
  
  // Fetch platform detection data when job is active
  const { data: platformData, loading: platformLoading } = usePlatformDetection(currentJobId);

  const handleFilesUploaded = (fileIds: string[]) => {
    setUploadedFileIds((prev) => {
      const merged = new Set(prev);
      fileIds.forEach((id) => merged.add(id));
      return Array.from(merged);
    });
  };

  const handleJobCreated = (jobId: string) => {
    setCurrentJobId(jobId);
    setJobStatus("queued");
  };

  const handleStatusChange = (status: string) => {
    setJobStatus(status);
  };

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      {/* Navigation Header */}
      <Header title="RCA Investigation" subtitle="Root Cause Analysis" />
      
      {/* Page Header */}
      <div className="border-b border-dark-border bg-dark-bg-secondary">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-fluent-blue-500/20">
              <svg
                className="h-6 w-6 text-fluent-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                />
              </svg>
            </div>
            <div>
              <h1 className="hero-title">Start New Investigation</h1>
              <p className="text-sm text-dark-text-tertiary">
                Upload files, configure analysis parameters, and stream results in real-time
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left Column: File Upload & Configuration */}
          <div className="space-y-6">
            {/* File Upload Section */}
            <div>
              <div className="mb-4">
                <h2 className="section-title">1. Upload Files</h2>
                <p className="text-sm text-dark-text-tertiary">
                  Upload logs, configs, or traces for analysis
                </p>
              </div>
              <FileUpload
                onFilesUploaded={handleFilesUploaded}
                jobId={currentJobId || undefined}
              />
            </div>

            {/* Job Configuration Section */}
            <div>
              <div className="mb-4">
                <h2 className="section-title">2. Configure Analysis</h2>
                <p className="text-sm text-dark-text-tertiary">
                  Select the model and parameters for the RCA job
                </p>
              </div>
              <JobConfigForm
                fileIds={uploadedFileIds}
                onSubmit={handleJobCreated}
                disabled={currentJobId !== null}
              />
            </div>

            {/* Status Info */}
            {currentJobId && (
              <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-fluent-blue-500/20">
                    <svg
                      className="h-5 w-5 text-fluent-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-dark-text-primary">
                      Analysis In Progress
                    </h3>
                    <p className="mt-1 text-xs text-dark-text-tertiary">
                      Job ID: <span className="font-mono">{currentJobId}</span>
                    </p>
                    <p className="mt-1 text-xs text-dark-text-tertiary">
                      Status: <span className="capitalize font-medium">{jobStatus}</span>
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Platform Detection Info */}
            {currentJobId && (platformData || platformLoading) && (
              <PlatformDetectionCard data={platformData} loading={platformLoading} />
            )}
          </div>

          {/* Right Column: Streaming Chat */}
          <div>
            <div className="mb-4">
              <h2 className="section-title">3. Live Analysis Stream</h2>
              <p className="text-sm text-dark-text-tertiary">
                Watch the RCA analysis happen in real-time
              </p>
            </div>
            <div className="h-[calc(100vh-12rem)]">
              <StreamingChat jobId={currentJobId} onStatusChange={handleStatusChange} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
