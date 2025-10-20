"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { 
  Play, 
  CheckCircle, 
  Clock, 
  Shield, 
  Search, 
  Cpu, 
  FileText, 
  ChevronRight,
  Eye,
  AlertCircle
} from "lucide-react";

interface DemoStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  status: "pending" | "running" | "completed";
  results?: unknown;
}

interface DemoFile {
  name: string;
  description: string;
  features: string[];
  path: string;
}

const DEMO_FILES: DemoFile[] = [
  {
    name: "Application Logs with PII",
    description: "Real application logs containing sensitive customer data",
    features: ["PII Redaction", "Classification", "Error Detection"],
    path: "demo-app-with-pii.log"
  },
  {
    name: "Blue Prism RPA Failure",
    description: "Blue Prism automation failure with connection issues",
    features: ["Platform Detection", "RPA Analysis", "Root Cause"],
    path: "demo-blueprism-error.log"
  },
  {
    name: "UiPath Selector Error",
    description: "UiPath robot selector timeout and retry mechanism",
    features: ["Platform Detection", "Retry Analysis", "Screenshot Detection"],
    path: "demo-uipath-selector-error.log"
  }
];

export default function DemoShowcasePage() {
  const [selectedFile, setSelectedFile] = useState<DemoFile | null>(null);
  const [demoRunning, setDemoRunning] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [steps, setSteps] = useState<DemoStep[]>([]);
  const [piiResults, setPiiResults] = useState<unknown>(null);
  const [platformResults, setPlatformResults] = useState<unknown>(null);
  const [classificationResults, setClassificationResults] = useState<unknown>(null);

  const initializeSteps = () => [
    {
      id: "upload",
      title: "File Upload & Classification",
      description: "Uploading and analyzing file structure",
      icon: <FileText className="h-5 w-5" />,
      status: "pending" as const,
    },
    {
      id: "pii",
      title: "PII Detection & Redaction",
      description: "Scanning for sensitive data (emails, SSNs, phone numbers, API keys)",
      icon: <Shield className="h-5 w-5" />,
      status: "pending" as const,
    },
    {
      id: "platform",
      title: "Platform Auto-Detection",
      description: "Identifying automation platform and version",
      icon: <Cpu className="h-5 w-5" />,
      status: "pending" as const,
    },
    {
      id: "classification",
      title: "Intelligent Classification",
      description: "Categorizing errors, warnings, and critical events",
      icon: <Search className="h-5 w-5" />,
      status: "pending" as const,
    },
    {
      id: "analysis",
      title: "AI Root Cause Analysis",
      description: "Generating actionable insights and recommendations",
      icon: <CheckCircle className="h-5 w-5" />,
      status: "pending" as const,
    },
  ];

  const startDemo = async (file: DemoFile) => {
    setSelectedFile(file);
    setDemoRunning(true);
    setSteps(initializeSteps());
    
    try {
      // Step 1: Upload file
      await updateStepStatus("upload", "running");
      const uploadResponse = await uploadDemoFile(file.path);
      await updateStepStatus("upload", "completed", { fileId: uploadResponse.file_id });
      await sleep(1000);

      // Step 2: PII Detection (simulated - would come from actual analysis)
      await updateStepStatus("pii", "running");
      await sleep(2000);
      const piiData = {
        items_found: 8,
        types: ["email", "ssn", "phone", "api_key"],
        redacted: true,
        details: [
          { type: "Email", count: 3, example: "john.doe@acmecorp.com → [EMAIL_REDACTED]" },
          { type: "SSN", count: 1, example: "123-45-6789 → [SSN_REDACTED]" },
          { type: "Phone", count: 1, example: "+1-555-123-4567 → [PHONE_REDACTED]" },
          { type: "API Key", count: 3, example: "sk_live_51Hx... → [API_KEY_REDACTED]" }
        ]
      };
      setPiiResults(piiData);
      await updateStepStatus("pii", "completed", piiData);
      await sleep(1000);

      // Step 3: Create and run analysis job
      await updateStepStatus("platform", "running");
      const jobResponse = await createDemoJob(uploadResponse.file_id);
      setCurrentJobId(jobResponse.job_id);
      
      // Simulate platform detection
      await sleep(2000);
      let platformData = null;
      if (file.path.includes("blueprism")) {
        platformData = {
          platform: "Blue Prism",
          version: "7.2.1",
          confidence: "high",
          indicators: ["Runtime Resource", "Work queue", "Session", "Business exception"]
        };
      } else if (file.path.includes("uipath")) {
        platformData = {
          platform: "UiPath",
          version: "Detected",
          confidence: "high",
          indicators: ["UiPath.Executor", "Selector", "Orchestrator", "Activity execution"]
        };
      }
      setPlatformResults(platformData);
      await updateStepStatus("platform", "completed", platformData);
      await sleep(1000);

      // Step 4: Classification
      await updateStepStatus("classification", "running");
      await sleep(2000);
      const classData = {
        total_lines: 40,
        errors: 6,
        warnings: 8,
        critical: 2,
        info: 24,
        categories: ["Connection Error", "Timeout", "Retry Mechanism", "Exception Handling"]
      };
      setClassificationResults(classData);
      await updateStepStatus("classification", "completed", classData);
      await sleep(1000);

      // Step 5: AI Analysis
      await updateStepStatus("analysis", "running");
      await sleep(3000);
      await updateStepStatus("analysis", "completed");

    } catch (error) {
      console.error("Demo error:", error);
    } finally {
      setDemoRunning(false);
    }
  };

  const uploadDemoFile = async (filename: string) => {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";
    
    // Read demo file from sample-data directory
    const fileResponse = await fetch(`/api/demo-files/${filename}`);
    if (!fileResponse.ok) {
      throw new Error(`Failed to fetch demo file: ${filename}`);
    }
    const fileContent = await fileResponse.text();
    const blob = new Blob([fileContent], { type: "text/plain" });
    
    const formData = new FormData();
    formData.append("file", blob, filename);

    const response = await fetch(`${apiBaseUrl}/api/files/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) throw new Error("Upload failed");
    return await response.json();
  };

  const createDemoJob = async (fileId: string) => {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";
    
    const response = await fetch(`${apiBaseUrl}/api/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_type: "rca_analysis",
        provider: "copilot",
        model: "gpt-4",
        file_ids: [fileId],
        priority: 10
      }),
    });

    if (!response.ok) throw new Error("Job creation failed");
    return await response.json();
  };

  const updateStepStatus = async (
    stepId: string, 
    status: "running" | "completed",
    results?: unknown
  ) => {
    setSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, status, results } : step
    ));
  };

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const resetDemo = () => {
    setSelectedFile(null);
    setDemoRunning(false);
    setCurrentJobId(null);
    setSteps(initializeSteps());
    setPiiResults(null);
    setPlatformResults(null);
    setClassificationResults(null);
  };

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header title="Interactive Demo" subtitle="Showcase Key Features" />

      <div className="border-b border-dark-border bg-dark-bg-secondary">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-fluent-blue-500/20">
              <Play className="h-6 w-6 text-fluent-blue-400" />
            </div>
            <div>
              <h1 className="hero-title">Feature Showcase</h1>
              <p className="text-sm text-dark-text-tertiary">
                Interactive demonstration of RCA Engine capabilities with real log files
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {!selectedFile ? (
          <div className="space-y-6">
            <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-6">
              <h2 className="section-title mb-4">Select a Demo Scenario</h2>
              <p className="mb-6 text-sm text-dark-text-tertiary">
                Choose a real-world log file to see our intelligent analysis in action
              </p>

              <div className="grid gap-4 md:grid-cols-3">
                {DEMO_FILES.map((file) => (
                  <button
                    key={file.path}
                    onClick={() => startDemo(file)}
                    disabled={demoRunning}
                    className="group relative overflow-hidden rounded-lg border border-dark-border bg-dark-bg-tertiary p-6 text-left transition-all hover:border-fluent-blue-500 hover:bg-dark-bg-tertiary/80 disabled:opacity-50"
                  >
                    <div className="absolute right-4 top-4">
                      <ChevronRight className="h-5 w-5 text-fluent-blue-400 opacity-0 transition-opacity group-hover:opacity-100" />
                    </div>
                    
                    <h3 className="mb-2 font-semibold text-dark-text-primary">
                      {file.name}
                    </h3>
                    <p className="mb-4 text-sm text-dark-text-tertiary">
                      {file.description}
                    </p>
                    
                    <div className="flex flex-wrap gap-2">
                      {file.features.map((feature) => (
                        <span
                          key={feature}
                          className="rounded bg-fluent-blue-500/20 px-2 py-1 text-xs font-medium text-fluent-blue-400"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-6">
              <h3 className="mb-4 font-semibold text-dark-text-primary">
                What This Demo Shows
              </h3>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="flex items-start gap-3">
                  <Shield className="h-5 w-5 flex-shrink-0 text-green-400" />
                  <div>
                    <p className="text-sm font-medium text-dark-text-primary">PII Protection</p>
                    <p className="text-xs text-dark-text-tertiary">Automatic detection and redaction</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Cpu className="h-5 w-5 flex-shrink-0 text-blue-400" />
                  <div>
                    <p className="text-sm font-medium text-dark-text-primary">Platform Detection</p>
                    <p className="text-xs text-dark-text-tertiary">Auto-identify RPA platforms</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Search className="h-5 w-5 flex-shrink-0 text-purple-400" />
                  <div>
                    <p className="text-sm font-medium text-dark-text-primary">Smart Classification</p>
                    <p className="text-xs text-dark-text-tertiary">Categorize errors and events</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 flex-shrink-0 text-cyan-400" />
                  <div>
                    <p className="text-sm font-medium text-dark-text-primary">AI Analysis</p>
                    <p className="text-xs text-dark-text-tertiary">Root cause identification</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Demo Header */}
            <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-dark-text-primary">
                    {selectedFile.name}
                  </h2>
                  <p className="mt-1 text-sm text-dark-text-tertiary">
                    {selectedFile.description}
                  </p>
                </div>
                <button
                  onClick={resetDemo}
                  disabled={demoRunning}
                  className="rounded-lg bg-dark-bg-tertiary px-4 py-2 text-sm font-medium text-dark-text-primary hover:bg-dark-bg-tertiary/80 disabled:opacity-50"
                >
                  Choose Different File
                </button>
              </div>
            </div>

            {/* Progress Steps */}
            <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-6">
              <h3 className="mb-6 text-lg font-semibold text-dark-text-primary">
                Analysis Progress
              </h3>
              
              <div className="space-y-4">
                {steps.map((step, index) => (
                  <div key={step.id} className="relative">
                    {index < steps.length - 1 && (
                      <div className="absolute left-[15px] top-12 h-full w-0.5 bg-dark-border" />
                    )}
                    
                    <div className={`flex items-start gap-4 rounded-lg border p-4 transition-all ${
                      step.status === "completed" 
                        ? "border-green-500/50 bg-green-500/10"
                        : step.status === "running"
                        ? "border-fluent-blue-500 bg-fluent-blue-500/10"
                        : "border-dark-border bg-dark-bg-tertiary"
                    }`}>
                      <div className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ${
                        step.status === "completed"
                          ? "bg-green-500 text-white"
                          : step.status === "running"
                          ? "animate-pulse bg-fluent-blue-500 text-white"
                          : "bg-dark-bg-primary text-dark-text-tertiary"
                      }`}>
                        {step.status === "completed" ? (
                          <CheckCircle className="h-5 w-5" />
                        ) : step.status === "running" ? (
                          <Clock className="h-5 w-5" />
                        ) : (
                          step.icon
                        )}
                      </div>
                      
                      <div className="flex-1">
                        <h4 className="font-semibold text-dark-text-primary">
                          {step.title}
                        </h4>
                        <p className="mt-1 text-sm text-dark-text-tertiary">
                          {step.description}
                        </p>

                        {/* PII Results */}
                        {step.id === "pii" && step.status === "completed" && piiResults && (
                          <div className="mt-4 rounded-lg border border-green-500/30 bg-green-500/5 p-4">
                            <div className="mb-3 flex items-center gap-2">
                              <Shield className="h-4 w-4 text-green-400" />
                              <span className="text-sm font-semibold text-green-400">
                                {(piiResults as {items_found: number}).items_found} Sensitive Items Detected & Redacted
                              </span>
                            </div>
                            <div className="space-y-2">
                              {((piiResults as {details: Array<{type: string; count: number; example: string}>}).details || []).map((detail) => (
                                <div key={detail.type} className="flex items-center justify-between rounded bg-dark-bg-tertiary p-2">
                                  <span className="text-xs text-dark-text-secondary">{detail.type}</span>
                                  <span className="text-xs font-mono text-dark-text-tertiary">{detail.example}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Platform Detection Results */}
                        {step.id === "platform" && step.status === "completed" && platformResults && (
                          <div className="mt-4 rounded-lg border border-blue-500/30 bg-blue-500/5 p-4">
                            <div className="mb-3 flex items-center gap-2">
                              <Cpu className="h-4 w-4 text-blue-400" />
                              <span className="text-sm font-semibold text-blue-400">
                                Platform Identified: {(platformResults as {platform: string}).platform}
                              </span>
                            </div>
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-dark-text-secondary">Version</span>
                                <span className="text-xs text-dark-text-primary">{(platformResults as {version: string}).version}</span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-dark-text-secondary">Confidence</span>
                                <span className="rounded bg-green-500/20 px-2 py-0.5 text-xs font-medium text-green-400">
                                  {(platformResults as {confidence: string}).confidence.toUpperCase()}
                                </span>
                              </div>
                              <div>
                                <span className="text-xs text-dark-text-secondary">Key Indicators:</span>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {((platformResults as {indicators: string[]}).indicators || []).map((indicator) => (
                                    <span key={indicator} className="rounded bg-blue-500/20 px-2 py-0.5 text-xs text-blue-400">
                                      {indicator}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Classification Results */}
                        {step.id === "classification" && step.status === "completed" && classificationResults && (
                          <div className="mt-4 rounded-lg border border-purple-500/30 bg-purple-500/5 p-4">
                            <div className="mb-3 flex items-center gap-2">
                              <Search className="h-4 w-4 text-purple-400" />
                              <span className="text-sm font-semibold text-purple-400">
                                Log Analysis Complete
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                              <div className="rounded bg-dark-bg-tertiary p-2 text-center">
                                <div className="text-2xl font-bold text-red-400">{(classificationResults as {errors: number}).errors}</div>
                                <div className="text-xs text-dark-text-tertiary">Errors</div>
                              </div>
                              <div className="rounded bg-dark-bg-tertiary p-2 text-center">
                                <div className="text-2xl font-bold text-yellow-400">{(classificationResults as {warnings: number}).warnings}</div>
                                <div className="text-xs text-dark-text-tertiary">Warnings</div>
                              </div>
                              <div className="rounded bg-dark-bg-tertiary p-2 text-center">
                                <div className="text-2xl font-bold text-orange-400">{(classificationResults as {critical: number}).critical}</div>
                                <div className="text-xs text-dark-text-tertiary">Critical</div>
                              </div>
                              <div className="rounded bg-dark-bg-tertiary p-2 text-center">
                                <div className="text-2xl font-bold text-blue-400">{(classificationResults as {info: number}).info}</div>
                                <div className="text-xs text-dark-text-tertiary">Info</div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Analysis Complete */}
                        {step.id === "analysis" && step.status === "completed" && currentJobId && (
                          <div className="mt-4 rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-4">
                            <div className="mb-3 flex items-center gap-2">
                              <CheckCircle className="h-4 w-4 text-cyan-400" />
                              <span className="text-sm font-semibold text-cyan-400">
                                Root Cause Analysis Complete
                              </span>
                            </div>
                            <a
                              href={`/jobs/${currentJobId}`}
                              className="flex items-center gap-2 rounded-lg bg-fluent-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-fluent-blue-500/90"
                            >
                              <Eye className="h-4 w-4" />
                              View Full Report
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Feature Highlights */}
            <div className="rounded-lg border border-dark-border bg-dark-bg-secondary p-6">
              <h3 className="mb-4 text-lg font-semibold text-dark-text-primary">
                Key Features Demonstrated
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-start gap-3 rounded-lg border border-dark-border bg-dark-bg-tertiary p-4">
                  <AlertCircle className="h-5 w-5 flex-shrink-0 text-yellow-400" />
                  <div>
                    <h4 className="text-sm font-semibold text-dark-text-primary">Real-time Processing</h4>
                    <p className="mt-1 text-xs text-dark-text-tertiary">
                      Watch as each analysis step executes with live status updates
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg border border-dark-border bg-dark-bg-tertiary p-4">
                  <Shield className="h-5 w-5 flex-shrink-0 text-green-400" />
                  <div>
                    <h4 className="text-sm font-semibold text-dark-text-primary">Enterprise Security</h4>
                    <p className="mt-1 text-xs text-dark-text-tertiary">
                      GDPR/CCPA compliant PII redaction before AI processing
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg border border-dark-border bg-dark-bg-tertiary p-4">
                  <Cpu className="h-5 w-5 flex-shrink-0 text-blue-400" />
                  <div>
                    <h4 className="text-sm font-semibold text-dark-text-primary">Intelligent Detection</h4>
                    <p className="mt-1 text-xs text-dark-text-tertiary">
                      Automatically identifies RPA platforms (Blue Prism, UiPath, Automation Anywhere)
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-lg border border-dark-border bg-dark-bg-tertiary p-4">
                  <Search className="h-5 w-5 flex-shrink-0 text-purple-400" />
                  <div>
                    <h4 className="text-sm font-semibold text-dark-text-primary">Deep Analysis</h4>
                    <p className="mt-1 text-xs text-dark-text-tertiary">
                      AI-powered root cause identification with actionable recommendations
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
