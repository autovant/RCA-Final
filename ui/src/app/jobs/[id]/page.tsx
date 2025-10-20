'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { ReportViewer } from '@/components/reports';
import { ArrowLeft, AlertCircle, Loader2 } from 'lucide-react';

interface JobOutputs {
  markdown?: string;
  html?: string;
  json?: Record<string, unknown>;
}

interface JobSummary {
  job_id: string;
  analysis_type?: string;
  generated_at?: string;
  outputs: JobOutputs;
  metrics?: Record<string, unknown>;
  ticketing?: Record<string, unknown>;
}

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [summary, setSummary] = useState<JobSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const fetchSummary = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`/api/summary/${jobId}`);
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Job not found or summary not yet available');
          }
          throw new Error(`Failed to load job summary: ${response.statusText}`);
        }

        const data = await response.json();
        setSummary(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [jobId]);

  // Determine severity from JSON data
  const severity = summary?.outputs?.json?.severity as 'critical' | 'high' | 'moderate' | 'low' | undefined;

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <Header />

      <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Back Button */}
        <button
          onClick={() => router.push('/jobs')}
          className="mb-6 flex items-center gap-2 text-fluent-blue-400 hover:text-fluent-blue-300 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="font-medium">Back to Jobs</span>
        </button>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-12 h-12 text-fluent-blue-400 animate-spin mb-4" />
            <p className="text-dark-text-secondary text-lg">Loading job report...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-red-400 font-semibold text-lg mb-1">Error Loading Report</h3>
              <p className="text-dark-text-secondary">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors font-medium"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Report Viewer */}
        {summary && !loading && !error && (
          <ReportViewer
            jobId={summary.job_id}
            markdown={summary.outputs.markdown}
            html={summary.outputs.html}
            json={summary.outputs.json}
            severity={severity}
            title={`${summary.analysis_type?.replace('_', ' ').toUpperCase() || 'RCA'} Report`}
          />
        )}

        {/* Additional Metadata Section */}
        {summary?.metrics && (
          <div className="mt-8 bg-dark-bg-secondary border border-dark-border rounded-xl p-6">
            <h3 className="text-xl font-semibold text-dark-text-primary mb-4 flex items-center gap-2">
              <span>📊</span>
              Analysis Metrics
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {Object.entries(summary.metrics).map(([key, value]) => (
                <div key={key} className="bg-dark-bg-tertiary rounded-lg p-4">
                  <p className="text-dark-text-tertiary text-sm mb-1">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </p>
                  <p className="text-dark-text-primary text-xl font-semibold">
                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Ticketing Info */}
        {summary?.ticketing && Object.keys(summary.ticketing).length > 0 && (
          <div className="mt-8 bg-dark-bg-secondary border border-dark-border rounded-xl p-6">
            <h3 className="text-xl font-semibold text-dark-text-primary mb-4 flex items-center gap-2">
              <span>🎫</span>
              Ticketing Information
            </h3>
            <pre className="bg-dark-bg-tertiary text-dark-text-primary p-4 rounded-lg overflow-x-auto text-sm">
              {JSON.stringify(summary.ticketing, null, 2)}
            </pre>
          </div>
        )}
      </main>
    </div>
  );
}
