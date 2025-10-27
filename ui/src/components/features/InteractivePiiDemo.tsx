"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui";

// PII Pattern configuration
const PII_PATTERNS = [
  { id: "email", label: "Email Addresses", regex: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, enabled: true },
  { id: "phone", label: "Phone Numbers", regex: /\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g, enabled: true },
  { id: "ssn", label: "SSN / Social Security", regex: /\b\d{3}-\d{2}-\d{4}\b/g, enabled: true },
  { id: "credit-card", label: "Credit Cards", regex: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, enabled: true },
  { id: "api-key", label: "API Keys", regex: /\b(sk_live_|pk_live_|sk_test_|pk_test_)[A-Za-z0-9]{24,}\b/g, enabled: true },
  { id: "jwt", label: "JWT Tokens", regex: /eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, enabled: true },
  { id: "ipv4", label: "IP Addresses", regex: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g, enabled: true },
  { id: "database", label: "Database Credentials", regex: /\b\w+\.(?:internal|db|database)\.[a-z0-9.-]+(?::\d{2,5})?\b/gi, enabled: true },
];

const SAMPLE_DATA = `[2025-10-20 08:15:23] INFO Application started successfully
[2025-10-20 08:15:24] INFO User john.doe@acmecorp.com logged in from 192.168.1.105
[2025-10-20 08:15:25] DEBUG Session token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
[2025-10-20 08:16:12] INFO Processing customer order for Jane Smith (SSN: 123-45-6789)
[2025-10-20 08:16:13] INFO Shipping to address: 742 Evergreen Terrace, Springfield, IL 62701
[2025-10-20 08:16:14] INFO Payment processed via credit card ending in 4532
[2025-10-20 08:16:15] DEBUG API Key: sk_test_EXAMPLE_fake_key_for_demo_only_12345
[2025-10-20 08:17:00] WARN Connection timeout to database server at db.internal.acmecorp.com:5432
[2025-10-20 08:17:01] ERROR Failed to establish connection after 3 retries
[2025-10-20 08:17:20] INFO Customer support ticket created for sarah.johnson@example.com
[2025-10-20 08:17:21] DEBUG Customer phone: +1-555-123-4567`;

type RedactionStats = {
  patternsDetected: number;
  itemsRedacted: number;
  securityWarnings: number;
  breakdown: Record<string, number>;
};

type InteractivePiiDemoProps = {
  onClose?: () => void;
};

export function InteractivePiiDemo({ onClose }: InteractivePiiDemoProps) {
  const [inputText, setInputText] = useState("");
  const [redactedText, setRedactedText] = useState("");
  const [patterns, setPatterns] = useState(PII_PATTERNS);
  const [stats, setStats] = useState<RedactionStats>({
    patternsDetected: 0,
    itemsRedacted: 0,
    securityWarnings: 0,
    breakdown: {},
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [hasRedacted, setHasRedacted] = useState(false);

  // Load sample data
  const loadSampleData = () => {
    setInputText(SAMPLE_DATA);
    setHasRedacted(false);
    setRedactedText("");
  };

  // Perform redaction
  const performRedaction = () => {
    if (!inputText.trim()) return;

    setIsProcessing(true);
    
    // Simulate processing delay for visual feedback
    setTimeout(() => {
      let result = inputText;
      const breakdown: Record<string, number> = {};
      let totalRedactions = 0;

      // Apply each enabled pattern
      patterns.forEach((pattern) => {
        if (pattern.enabled) {
          const matches = inputText.match(pattern.regex);
          const count = matches ? matches.length : 0;
          
          if (count > 0) {
            breakdown[pattern.id] = count;
            totalRedactions += count;
            result = result.replace(pattern.regex, "[REDACTED]");
          }
        }
      });

      const patternsDetectedCount = Object.keys(breakdown).length;

      setRedactedText(result);
      setStats({
        patternsDetected: patternsDetectedCount,
        itemsRedacted: totalRedactions,
        securityWarnings: 0,
        breakdown,
      });
      setHasRedacted(true);
      setIsProcessing(false);
    }, 500);
  };

  // Toggle pattern
  const togglePattern = (id: string) => {
    setPatterns((prev) =>
      prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p))
    );
    
    // Re-redact if we've already processed
    if (hasRedacted) {
      setTimeout(() => performRedaction(), 100);
    }
  };

  // Select/deselect all
  const selectAll = () => {
    setPatterns((prev) => prev.map((p) => ({ ...p, enabled: true })));
    if (hasRedacted) setTimeout(() => performRedaction(), 100);
  };

  const deselectAll = () => {
    setPatterns((prev) => prev.map((p) => ({ ...p, enabled: false })));
    if (hasRedacted) setTimeout(() => performRedaction(), 100);
  };

  // Auto-update stats when patterns change
  useEffect(() => {
    if (inputText && hasRedacted) {
      const updateRedaction = () => {
        let result = inputText;
        const breakdown: Record<string, number> = {};
        let totalRedactions = 0;

        patterns.forEach((pattern) => {
          if (pattern.enabled) {
            const matches = inputText.match(pattern.regex);
            const count = matches ? matches.length : 0;
            
            if (count > 0) {
              breakdown[pattern.id] = count;
              totalRedactions += count;
              result = result.replace(pattern.regex, "[REDACTED]");
            }
          }
        });

        const patternsDetectedCount = Object.keys(breakdown).length;

        setRedactedText(result);
        setStats({
          patternsDetected: patternsDetectedCount,
          itemsRedacted: totalRedactions,
          securityWarnings: 0,
          breakdown,
        });
      };
      
      updateRedaction();
    }
  }, [patterns, inputText, hasRedacted]);

  return (
    <div className="interactive-pii-demo space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-bold flex items-center gap-2">
          🔒 Interactive Demo: Try It Live
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            aria-label="Close demo"
            title="Close demo"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Input Section */}
      <div className="demo-input space-y-3">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Paste your logs or sample data here:
        </label>
        <textarea
          className="w-full h-48 p-4 border border-gray-300 dark:border-gray-600 rounded-lg font-mono text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Paste application logs, error messages, or any text containing sensitive data..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          data-testid="pii-demo-input"
        />
        <div className="flex gap-3">
          <Button
            onClick={loadSampleData}
            variant="secondary"
            className="flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Load Sample Data
          </Button>
          <Button
            onClick={performRedaction}
            disabled={!inputText.trim() || isProcessing}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isProcessing ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Redact PII Now
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Statistics Panel */}
      {hasRedacted && (
        <div className="stats-panel grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="pii-stats-panel">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-1">
              📊 Patterns Detected
            </div>
            <div className="text-3xl font-bold text-blue-900 dark:text-blue-100">
              {stats.patternsDetected}
            </div>
            <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
              Pattern Types Found
            </div>
          </div>

          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <div className="text-sm text-green-600 dark:text-green-400 font-medium mb-1">
              🔒 Items Redacted
            </div>
            <div className="text-3xl font-bold text-green-900 dark:text-green-100">
              {stats.itemsRedacted}
            </div>
            <div className="text-xs text-green-600 dark:text-green-400 mt-1">
              Sensitive Items Protected
            </div>
          </div>

          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <div className="text-sm text-amber-600 dark:text-amber-400 font-medium mb-1">
              ⚠️ Security Warnings
            </div>
            <div className="text-3xl font-bold text-amber-900 dark:text-amber-100">
              {stats.securityWarnings}
            </div>
            <div className="text-xs text-amber-600 dark:text-amber-400 mt-1">
              Potential Issues Detected
            </div>
          </div>
        </div>
      )}

      {/* Pattern Selection */}
      <div className="pattern-toggles space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Select Patterns to Redact:
          </label>
          <div className="flex gap-2">
            <button
              onClick={selectAll}
              className="text-xs px-3 py-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-700 dark:text-gray-300"
              aria-label="Select all pattern types"
              title="Select all pattern types"
            >
              Select All
            </button>
            <button
              onClick={deselectAll}
              className="text-xs px-3 py-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-700 dark:text-gray-300"
              aria-label="Deselect all pattern types"
              title="Deselect all pattern types"
            >
              Deselect All
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
          {patterns.map((pattern) => {
            const count = stats.breakdown[pattern.id] || 0;
            return (
              <label
                key={pattern.id}
                className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${
                  pattern.enabled
                    ? "bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700"
                    : "bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={pattern.enabled}
                  onChange={() => togglePattern(pattern.id)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm flex-1 text-gray-900 dark:text-gray-100">
                  {pattern.label}
                </span>
                {hasRedacted && (
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    ({count})
                  </span>
                )}
              </label>
            );
          })}
        </div>
      </div>

      {/* Before/After Comparison */}
      {hasRedacted && (
        <div className="comparison-grid grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="before-panel border border-red-300 dark:border-red-800 rounded-lg overflow-hidden">
            <div className="bg-red-50 dark:bg-red-900/20 px-4 py-2 border-b border-red-300 dark:border-red-800">
              <h4 className="text-sm font-semibold text-red-900 dark:text-red-100 flex items-center gap-2">
                ❌ Before Redaction
                <span className="text-xs text-red-600 dark:text-red-400 font-normal">
                  (Original Content)
                </span>
              </h4>
            </div>
            <pre className="p-4 text-xs font-mono overflow-x-auto bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 max-h-96 overflow-y-auto">
              {inputText}
            </pre>
          </div>

          <div className="after-panel border border-green-300 dark:border-green-800 rounded-lg overflow-hidden">
            <div className="bg-green-50 dark:bg-green-900/20 px-4 py-2 border-b border-green-300 dark:border-green-800">
              <h4 className="text-sm font-semibold text-green-900 dark:text-green-100 flex items-center gap-2">
                ✅ After Redaction
                <span className="text-xs text-green-600 dark:text-green-400 font-normal">
                  (Protected Content)
                </span>
              </h4>
            </div>
            <pre className="p-4 text-xs font-mono overflow-x-auto bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 max-h-96 overflow-y-auto">
              {redactedText}
            </pre>
          </div>
        </div>
      )}

      {/* Security Status */}
      {hasRedacted && (
        <div
          className={`security-status p-4 rounded-lg border ${
            stats.itemsRedacted > 0
              ? "bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700"
              : "bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700"
          }`}
        >
          <div className="flex items-center gap-3">
            <div className="text-2xl">
              {stats.itemsRedacted > 0 ? "✅" : "⚠️"}
            </div>
            <div className="flex-1">
              <div className="font-semibold text-sm">
                {stats.itemsRedacted > 0
                  ? "PROTECTED: All sensitive data successfully redacted"
                  : "NO PII DETECTED: Safe to proceed"}
              </div>
              <div className="text-xs mt-1 text-gray-600 dark:text-gray-400">
                {stats.itemsRedacted > 0
                  ? "Safe to share with LLMs and external systems"
                  : "No sensitive patterns found in your content"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pattern Breakdown */}
      {hasRedacted && stats.itemsRedacted > 0 && (
        <div className="pattern-breakdown">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Redaction Breakdown by Pattern Type:
          </h4>
          <div className="space-y-2">
            {Object.entries(stats.breakdown).map(([patternId, count]) => {
              const pattern = patterns.find((p) => p.id === patternId);
              return (
                <div
                  key={patternId}
                  className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded"
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {pattern?.label || patternId}
                  </span>
                  <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                    {count} {count === 1 ? "instance" : "instances"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default InteractivePiiDemo;
