/**
 * Interactive Demo Framework with Feedback and Analytics
 * 
 * Provides enhanced interactive demos with:
 * - Real-time feedback collection
 * - Usage analytics tracking
 * - Comparison views
 * - Exportable results
 */

"use client";

import { useState, useCallback, useEffect } from "react";
import { 
  ThumbsUp, 
  ThumbsDown, 
  MessageSquare, 
  Download, 
  Share2,
  BarChart3,
  Copy,
  CheckCircle,
  XCircle
} from "lucide-react";

// ============================================================================
// Types
// ============================================================================

export interface DemoFeedback {
  demoId: string;
  rating: "positive" | "negative" | null;
  comment?: string;
  timestamp: string;
  useful: boolean;
  categories: string[];
}

export interface DemoAnalytics {
  demoId: string;
  startTime: string;
  endTime?: string;
  duration?: number;
  stepsCompleted: number;
  totalSteps: number;
  interactions: Array<{
    type: string;
    timestamp: string;
    details?: any;
  }>;
}

export interface ComparisonResult {
  label: string;
  before: any;
  after: any;
  improvement?: string;
  metadata?: Record<string, any>;
}

// ============================================================================
// Feedback Component
// ============================================================================

interface FeedbackPanelProps {
  demoId: string;
  onSubmit?: (feedback: DemoFeedback) => void;
  categories?: string[];
}

export function FeedbackPanel({ 
  demoId, 
  onSubmit,
  categories = ["Accuracy", "Speed", "Ease of Use", "Documentation"]
}: FeedbackPanelProps) {
  const [rating, setRating] = useState<"positive" | "negative" | null>(null);
  const [comment, setComment] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = useCallback(() => {
    const feedback: DemoFeedback = {
      demoId,
      rating,
      comment: comment.trim() || undefined,
      timestamp: new Date().toISOString(),
      useful: rating === "positive",
      categories: selectedCategories,
    };

    onSubmit?.(feedback);
    
    // Send to backend
    fetch("/api/feedback/demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(feedback),
    }).catch(err => console.error("Failed to submit feedback:", err));

    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  }, [demoId, rating, comment, selectedCategories, onSubmit]);

  const toggleCategory = (category: string) => {
    setSelectedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  if (submitted) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
        <p className="text-green-800 font-medium">Thank you for your feedback!</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">How was this demo?</h3>
      
      {/* Rating Buttons */}
      <div className="flex gap-4">
        <button
          onClick={() => setRating("positive")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-colors ${
            rating === "positive"
              ? "border-green-500 bg-green-50 text-green-700"
              : "border-gray-300 hover:border-green-400 text-gray-700"
          }`}
        >
          <ThumbsUp className="h-5 w-5" />
          <span className="font-medium">Helpful</span>
        </button>
        
        <button
          onClick={() => setRating("negative")}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-colors ${
            rating === "negative"
              ? "border-red-500 bg-red-50 text-red-700"
              : "border-gray-300 hover:border-red-400 text-gray-700"
          }`}
        >
          <ThumbsDown className="h-5 w-5" />
          <span className="font-medium">Not Helpful</span>
        </button>
      </div>

      {/* Category Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          What aspects stood out?
        </label>
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <button
              key={category}
              onClick={() => toggleCategory(category)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                selectedCategories.includes(category)
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* Comment Field */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Additional feedback (optional)
        </label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Tell us more about your experience..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
          rows={3}
        />
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={rating === null}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        <MessageSquare className="h-4 w-4" />
        Submit Feedback
      </button>
    </div>
  );
}

// ============================================================================
// Analytics Tracker
// ============================================================================

export class DemoAnalyticsTracker {
  private analytics: DemoAnalytics;
  private intervalId?: NodeJS.Timeout;

  constructor(demoId: string, totalSteps: number) {
    this.analytics = {
      demoId,
      startTime: new Date().toISOString(),
      stepsCompleted: 0,
      totalSteps,
      interactions: [],
    };
  }

  trackInteraction(type: string, details?: any) {
    this.analytics.interactions.push({
      type,
      timestamp: new Date().toISOString(),
      details,
    });
  }

  trackStepComplete() {
    this.analytics.stepsCompleted++;
    this.trackInteraction("step_complete", {
      step: this.analytics.stepsCompleted,
    });
  }

  complete() {
    this.analytics.endTime = new Date().toISOString();
    this.analytics.duration = 
      new Date(this.analytics.endTime).getTime() - 
      new Date(this.analytics.startTime).getTime();

    // Send to backend
    fetch("/api/analytics/demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(this.analytics),
    }).catch(err => console.error("Failed to send analytics:", err));

    return this.analytics;
  }

  getAnalytics(): DemoAnalytics {
    return { ...this.analytics };
  }
}

// ============================================================================
// Comparison View Component
// ============================================================================

interface ComparisonViewProps {
  results: ComparisonResult[];
  title?: string;
}

export function ComparisonView({ results, title = "Before & After Comparison" }: ComparisonViewProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      
      <div className="space-y-4">
        {results.map((result, index) => (
          <div key={index} className="border-b border-gray-200 last:border-0 pb-4 last:pb-0">
            <h4 className="font-medium text-gray-800 mb-3">{result.label}</h4>
            
            <div className="grid grid-cols-2 gap-4">
              {/* Before */}
              <div className="bg-red-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="text-sm font-medium text-red-800">Before</span>
                </div>
                <pre className="text-xs text-gray-700 overflow-auto">
                  {JSON.stringify(result.before, null, 2)}
                </pre>
              </div>
              
              {/* After */}
              <div className="bg-green-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium text-green-800">After</span>
                </div>
                <pre className="text-xs text-gray-700 overflow-auto">
                  {JSON.stringify(result.after, null, 2)}
                </pre>
              </div>
            </div>
            
            {result.improvement && (
              <div className="mt-2 flex items-center gap-2 text-sm text-green-700 bg-green-50 px-3 py-2 rounded">
                <BarChart3 className="h-4 w-4" />
                <span>{result.improvement}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Export Component
// ============================================================================

interface ExportButtonProps {
  data: any;
  filename: string;
  format?: "json" | "csv" | "markdown";
  label?: string;
}

export function ExportButton({ 
  data, 
  filename, 
  format = "json",
  label = "Export Results"
}: ExportButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleExport = useCallback(() => {
    let content: string;
    let mimeType: string;
    let extension: string;

    switch (format) {
      case "json":
        content = JSON.stringify(data, null, 2);
        mimeType = "application/json";
        extension = "json";
        break;
      
      case "csv":
        // Simple CSV conversion (assumes flat object or array of objects)
        if (Array.isArray(data)) {
          const headers = Object.keys(data[0] || {}).join(",");
          const rows = data.map(row => 
            Object.values(row).map(v => 
              typeof v === "string" && v.includes(",") ? `"${v}"` : v
            ).join(",")
          );
          content = [headers, ...rows].join("\n");
        } else {
          content = Object.entries(data).map(([k, v]) => `${k},${v}`).join("\n");
        }
        mimeType = "text/csv";
        extension = "csv";
        break;
      
      case "markdown":
        content = `# ${filename}\n\n\`\`\`json\n${JSON.stringify(data, null, 2)}\n\`\`\``;
        mimeType = "text/markdown";
        extension = "md";
        break;
      
      default:
        content = String(data);
        mimeType = "text/plain";
        extension = "txt";
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [data, filename, format]);

  const handleCopy = useCallback(() => {
    const content = JSON.stringify(data, null, 2);
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [data]);

  return (
    <div className="flex gap-2">
      <button
        onClick={handleExport}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
      >
        <Download className="h-4 w-4" />
        {label}
      </button>
      
      <button
        onClick={handleCopy}
        className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
      >
        {copied ? (
          <>
            <CheckCircle className="h-4 w-4" />
            Copied!
          </>
        ) : (
          <>
            <Copy className="h-4 w-4" />
            Copy
          </>
        )}
      </button>
    </div>
  );
}

// ============================================================================
// Share Component
// ============================================================================

interface ShareButtonProps {
  demoId: string;
  results?: any;
  label?: string;
}

export function ShareButton({ demoId, results, label = "Share Demo" }: ShareButtonProps) {
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleShare = useCallback(async () => {
    // Generate shareable link
    const payload = {
      demoId,
      results,
      timestamp: new Date().toISOString(),
    };

    try {
      const response = await fetch("/api/share/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const { shareId } = await response.json();
      const url = `${window.location.origin}/share/${shareId}`;
      setShareUrl(url);

      // Copy to clipboard
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to generate share link:", err);
    }
  }, [demoId, results]);

  return (
    <div className="space-y-2">
      <button
        onClick={handleShare}
        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
      >
        <Share2 className="h-4 w-4" />
        {label}
      </button>

      {shareUrl && (
        <div className="flex items-center gap-2 p-2 bg-green-50 border border-green-200 rounded-lg">
          <span className="flex-1 text-sm text-green-800 font-mono truncate">
            {shareUrl}
          </span>
          {copied && (
            <span className="text-xs text-green-600 font-medium">Copied!</span>
          )}
        </div>
      )}
    </div>
  );
}
