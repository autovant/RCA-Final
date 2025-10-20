"use client";

import Link from "next/link";
import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui";

// Feature data structure
type Feature = {
  id: string;
  title: string;
  icon: React.ReactNode;
  description: string;
  benefits: string[];
  capabilities: string[];
  useCases: string[];
  status?: "stable" | "beta" | "new";
};

// Feature definitions
const features: Feature[] = [
  {
    id: "conversational-rca",
    title: "Conversational RCA Engine",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    description: "Multi-turn LLM reasoning engine that performs deep root cause analysis with full conversation traceability and context preservation.",
    benefits: [
      "Persistent conversation history for audit trails",
      "Multi-turn reasoning for complex scenarios",
      "Context-aware analysis with retrieval augmentation",
      "Supports multiple automation platforms"
    ],
    capabilities: [
      "Chunking & embedding with pgvector",
      "Retrieval-augmented generation (RAG)",
      "Configurable conversation depth",
      "Automatic evidence linking"
    ],
    useCases: [
      "Blue Prism automation failures",
      "Appian process exceptions",
      "PEGA workflow errors",
      "Custom automation log analysis"
    ],
    status: "stable"
  },
  {
    id: "multi-llm",
    title: "Multi-Provider LLM Support",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
    description: "Flexible LLM provider layer supporting Ollama, OpenAI, and AWS Bedrock with per-job model overrides and automatic fallback.",
    benefits: [
      "Provider agnostic architecture",
      "Per-job model selection",
      "Automatic fallback handling",
      "Cost optimization options"
    ],
    capabilities: [
      "Ollama/local model support",
      "OpenAI API integration",
      "AWS Bedrock compatibility",
      "Custom provider plugins"
    ],
    useCases: [
      "On-premise deployments with local models",
      "Cloud-based analysis with OpenAI",
      "Enterprise AWS Bedrock integration",
      "Hybrid multi-cloud strategies"
    ],
    status: "stable"
  },
  {
    id: "pii-redaction",
    title: "🔒 Enterprise PII Protection",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    description: "Military-grade, multi-layered PII redaction system with 30+ pattern types, multi-pass scanning, and strict validation to ensure zero sensitive data leakage to LLMs or outputs.",
    benefits: [
      "30+ sensitive data patterns protected (AWS/Azure keys, JWT tokens, passwords, DB credentials)",
      "Multi-pass scanning catches nested and revealed patterns",
      "Strict validation mode detects potential leaks with security warnings",
      "Real-time visibility with live stats and security indicators",
      "Complete audit trail for compliance (GDPR, PCI DSS, HIPAA, SOC 2)",
      "Enabled by default - zero configuration needed"
    ],
    capabilities: [
      "Cloud provider credentials (AWS, Azure, GCP)",
      "Authentication secrets (JWT, OAuth, Bearer tokens, API keys)",
      "Database connection strings (MongoDB, PostgreSQL, MySQL)",
      "Cryptographic material (private keys, SSH keys)",
      "Network identifiers (IPv4, IPv6, MAC addresses)",
      "Personal data (email, phone, SSN, credit cards)",
      "Environment variables and base64 secrets",
      "URLs with embedded credentials",
      "Multi-pass redaction (up to 3 passes)",
      "Post-redaction validation with 6 security checks"
    ],
    useCases: [
      "Zero-trust log analysis with cloud credentials",
      "GDPR/HIPAA compliant data processing",
      "Financial services with PCI DSS requirements",
      "Government/defense with classified data",
      "Multi-tenant SaaS with strict data isolation",
      "Security incident investigation with credential exposure"
    ],
    status: "stable"
  },
  {
    id: "itsm-ticketing",
    title: "ITSM Ticketing Integration",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    description: "Comprehensive ServiceNow and Jira integration with feature toggles, dual-tracking mode, and customizable field mappings.",
    benefits: [
      "Automatic ticket creation",
      "Dual-platform tracking",
      "Dry-run preview mode",
      "Real-time status sync"
    ],
    capabilities: [
      "ServiceNow incident management",
      "Jira issue creation",
      "Custom field mapping",
      "Template-based tickets",
      "Profile-based credentials"
    ],
    useCases: [
      "Automated incident reporting",
      "Cross-platform ticket linking",
      "Executive escalation workflows",
      "SLA-driven ticket creation"
    ],
    status: "stable"
  },
  {
    id: "file-watcher",
    title: "Intelligent File Watcher",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
    ),
    description: "Monitors directories for new log files and automatically triggers RCA jobs with configurable filters, MIME validation, and security controls.",
    benefits: [
      "Zero-touch automation",
      "Configurable file patterns",
      "Secure sandboxing",
      "Real-time SSE updates"
    ],
    capabilities: [
      "Include/exclude glob patterns",
      "MIME type validation",
      "File size limits",
      "Allowlisted directories",
      "Event bus integration"
    ],
    useCases: [
      "Continuous log monitoring",
      "Automated batch processing",
      "Production incident detection",
      "Multi-environment watching"
    ],
    status: "stable"
  },
  {
    id: "sse-streaming",
    title: "Real-Time SSE Streaming",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    description: "Server-Sent Events (SSE) streaming for live job progress, status updates, and watcher events with automatic reconnection.",
    benefits: [
      "Real-time progress tracking",
      "Live dashboard updates",
      "No polling overhead",
      "Automatic reconnection"
    ],
    capabilities: [
      "Job status streaming",
      "Progress event updates",
      "Watcher file detection",
      "Error event broadcasting",
      "Client-side reconnection logic"
    ],
    useCases: [
      "Live operation dashboards",
      "Real-time monitoring",
      "Event-driven UI updates",
      "Executive briefing displays"
    ],
    status: "stable"
  },
  {
    id: "structured-outputs",
    title: "Structured RCA Outputs",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    description: "Every analysis produces Markdown, HTML, and JSON outputs with severity levels, recommended actions, and ticket metadata.",
    benefits: [
      "Multiple output formats",
      "Structured data extraction",
      "Executive-ready reports",
      "API-friendly JSON"
    ],
    capabilities: [
      "Markdown summaries",
      "Formatted HTML reports",
      "Structured JSON data",
      "Severity classification",
      "Action recommendations",
      "Metadata enrichment"
    ],
    useCases: [
      "Executive briefings",
      "Automated reporting",
      "Integration with other systems",
      "Historical analysis storage"
    ],
    status: "stable"
  },
  {
    id: "observability",
    title: "Full Observability Stack",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    description: "Comprehensive metrics, tracing, and structured logging with Prometheus integration and job-level correlation.",
    benefits: [
      "Prometheus metrics export",
      "Job event tracing",
      "Structured JSON logs",
      "Performance analytics"
    ],
    capabilities: [
      "Job lifecycle metrics",
      "Ticket creation latency",
      "Watcher event tracking",
      "OpenTelemetry support",
      "Grafana dashboard integration"
    ],
    useCases: [
      "Performance monitoring",
      "SLA tracking",
      "Capacity planning",
      "Incident analysis"
    ],
    status: "stable"
  },
  {
    id: "executive-ui",
    title: "Executive Control Plane",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    description: "Modern React/Next.js interface with Fluent Design aesthetics, dark mode, and real-time job monitoring.",
    benefits: [
      "Intuitive drag-and-drop upload",
      "Real-time status updates",
      "Responsive mobile design",
      "Accessible components"
    ],
    capabilities: [
      "File upload interface",
      "Job configuration forms",
      "Live SSE streaming display",
      "Ticket management dashboard",
      "Watcher configuration panel",
      "Conversation history viewer"
    ],
    useCases: [
      "Executive operations dashboards",
      "Support team interfaces",
      "Incident command centers",
      "Mobile monitoring"
    ],
    status: "stable"
  },
  {
    id: "platform-detection",
    title: "Intelligent Platform Detection",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
    description: "Automatically detects automation platforms (Blue Prism, Appian, PEGA) from log content and adapts analysis strategies.",
    benefits: [
      "Zero configuration required",
      "Platform-specific insights",
      "Adaptive analysis",
      "Multi-platform support"
    ],
    capabilities: [
      "Blue Prism log detection",
      "Appian process identification",
      "PEGA workflow recognition",
      "Custom platform patterns",
      "Confidence scoring"
    ],
    useCases: [
      "Multi-vendor environments",
      "Automated platform routing",
      "Specialized analysis paths",
      "Platform migration tracking"
    ],
    status: "beta"
  },
  {
    id: "archive-support",
    title: "Archive Format Support",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
      </svg>
    ),
    description: "Native support for ZIP, TAR, and compressed archives with secure extraction and automatic content processing.",
    benefits: [
      "Bulk file processing",
      "Secure extraction",
      "Memory-efficient streaming",
      "Nested archive support"
    ],
    capabilities: [
      "ZIP file extraction",
      "TAR archive processing",
      "GZIP/BZ2 decompression",
      "Path traversal prevention",
      "Size limit enforcement"
    ],
    useCases: [
      "Batch log uploads",
      "Historical data analysis",
      "Automated log collection",
      "Multi-file investigations"
    ],
    status: "stable"
  },
  {
    id: "security",
    title: "Enterprise Security",
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    description: "Non-root containers, read-only filesystems, JWT authentication, MIME validation, and secrets management.",
    benefits: [
      "Zero-trust architecture",
      "Defense in depth",
      "Compliance-ready",
      "Audit trail"
    ],
    capabilities: [
      "JWT with audience claims",
      "RBAC with scope control",
      "MIME + magic number validation",
      "CSP without unsafe-inline",
      "Secrets via environment/vault",
      "Container hardening"
    ],
    useCases: [
      "Enterprise deployments",
      "Multi-tenant environments",
      "Regulated industries",
      "Zero-trust networks"
    ],
    status: "stable"
  }
];

export default function FeaturesPage() {
  const [selectedFeature, setSelectedFeature] = useState<Feature>(features[0]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "new":
        return (
          <span className="ml-2 inline-flex items-center rounded-full bg-fluent-success/20 px-2 py-0.5 text-xs font-medium text-fluent-success ring-1 ring-inset ring-fluent-success/30">
            NEW
          </span>
        );
      case "beta":
        return (
          <span className="ml-2 inline-flex items-center rounded-full bg-fluent-warning/20 px-2 py-0.5 text-xs font-medium text-fluent-warning ring-1 ring-inset ring-fluent-warning/30">
            BETA
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header title="RCA Features" subtitle="Comprehensive Feature Showcase" />
      
      <div className="container mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-dark-text-primary mb-4">
            Platform Features
          </h1>
          <p className="text-lg text-dark-text-secondary max-w-3xl mx-auto">
            Discover the comprehensive capabilities of the RCA Insight Engine—from intelligent automation 
            to enterprise-grade security and seamless ITSM integration.
          </p>
          <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
            <Link href="/demo">
              <Button size="lg" className="uppercase tracking-[0.24em]">
                Launch Guided Demo
              </Button>
            </Link>
            <Link href="/investigation">
              <Button size="lg" variant="ghost" className="uppercase tracking-[0.24em]">
                Start Investigation
              </Button>
            </Link>
          </div>
        </div>

        {/* Mobile Toggle Button */}
        <div className="lg:hidden mb-4">
          <Button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            variant="secondary"
            className="w-full"
            icon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            }
          >
            {isSidebarOpen ? "Hide" : "Show"} Feature Menu
          </Button>
        </div>

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sidebar */}
          <aside
            className={`lg:col-span-3 ${
              isSidebarOpen ? "block" : "hidden"
            } lg:block transition-all duration-300`}
          >
            <div className="card sticky top-24 p-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
              <h2 className="text-sm font-semibold text-dark-text-tertiary uppercase tracking-wider mb-4">
                Features
              </h2>
              <nav className="space-y-1">
                {features.map((feature) => (
                  <button
                    key={feature.id}
                    onClick={() => {
                      setSelectedFeature(feature);
                      if (window.innerWidth < 1024) {
                        setIsSidebarOpen(false);
                      }
                    }}
                    className={`w-full text-left px-3 py-3 rounded-lg transition-all duration-200 flex items-start gap-3 group ${
                      selectedFeature.id === feature.id
                        ? "bg-gradient-to-r from-fluent-blue-500/20 to-fluent-info/10 text-dark-text-primary border border-fluent-blue-500/40"
                        : "hover:bg-dark-bg-elevated/50 text-dark-text-secondary hover:text-dark-text-primary"
                    }`}
                  >
                    <div
                      className={`mt-0.5 ${
                        selectedFeature.id === feature.id
                          ? "text-fluent-blue-400"
                          : "text-dark-text-tertiary group-hover:text-fluent-blue-400"
                      }`}
                    >
                      {feature.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        {feature.title}
                      </div>
                      {feature.status && feature.status !== "stable" && (
                        <span className={`mt-1 inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                          feature.status === "beta"
                            ? "bg-fluent-warning/20 text-fluent-warning"
                            : "bg-fluent-success/20 text-fluent-success"
                        }`}>
                          {feature.status.toUpperCase()}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </nav>
            </div>
          </aside>

          {/* Content Area */}
          <main className="lg:col-span-9">
            <div className="card p-8 animate-fade-in">
              {/* Feature Header */}
              <div className="flex items-start gap-4 mb-6 pb-6 border-b border-dark-border/40">
                <div className="p-4 rounded-2xl bg-gradient-to-br from-fluent-blue-500/20 to-fluent-info/10 text-fluent-blue-400 border border-fluent-blue-500/30">
                  {selectedFeature.icon}
                </div>
                <div className="flex-1">
                  <h2 className="text-3xl font-bold text-dark-text-primary flex items-center">
                    {selectedFeature.title}
                    {getStatusBadge(selectedFeature.status)}
                  </h2>
                  <p className="mt-2 text-lg text-dark-text-secondary">
                    {selectedFeature.description}
                  </p>
                </div>
              </div>

              {/* Benefits Section */}
              <div className="mb-8">
                <h3 className="text-xl font-semibold text-dark-text-primary mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-fluent-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Key Benefits
                </h3>
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {selectedFeature.benefits.map((benefit, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-3 p-3 rounded-lg bg-dark-bg-elevated/30 border border-dark-border/20 hover:border-fluent-blue-500/30 transition-colors"
                    >
                      <svg
                        className="w-5 h-5 text-fluent-success mt-0.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-dark-text-secondary">{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Capabilities Section */}
              <div className="mb-8">
                <h3 className="text-xl font-semibold text-dark-text-primary mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-fluent-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Technical Capabilities
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedFeature.capabilities.map((capability, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-2 rounded-lg bg-gradient-to-r from-fluent-blue-500/10 to-fluent-info/5 text-dark-text-primary border border-fluent-blue-500/20 text-sm font-medium hover:border-fluent-blue-500/40 transition-colors"
                    >
                      {capability}
                    </span>
                  ))}
                </div>
              </div>

              {/* Use Cases Section */}
              <div>
                <h3 className="text-xl font-semibold text-dark-text-primary mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-fluent-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  Common Use Cases
                </h3>
                <ul className="space-y-3">
                  {selectedFeature.useCases.map((useCase, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-3 p-4 rounded-lg bg-dark-bg-elevated/30 border border-dark-border/20 hover:border-fluent-warning/30 transition-all hover:shadow-fluent"
                    >
                      <div className="p-1 rounded-full bg-fluent-warning/20 text-fluent-warning mt-0.5">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <span className="text-dark-text-secondary flex-1">{useCase}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Call to Action */}
            <div className="mt-6 card p-6 bg-gradient-to-r from-fluent-blue-500/10 via-fluent-info/5 to-transparent border-fluent-blue-500/30">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-dark-text-primary mb-1">
                    Ready to explore {selectedFeature.title}?
                  </h3>
                  <p className="text-sm text-dark-text-tertiary">
                    Try it out in the investigation panel or check the documentation for detailed integration guides.
                  </p>
                </div>
                <div className="flex gap-3">
                  <Button
                    variant="primary"
                    onClick={() => window.location.href = "/investigation"}
                    icon={
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                    }
                  >
                    Try Now
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => window.location.href = "/docs"}
                    icon={
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                    }
                  >
                    Documentation
                  </Button>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
