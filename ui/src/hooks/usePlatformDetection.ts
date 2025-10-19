/**
 * Hook for fetching platform detection data
 */

import { useEffect, useState } from "react";

interface PlatformEntity {
  entity_type: string;
  value: string;
  source_file?: string;
}

export interface PlatformDetectionData {
  job_id: string;
  detected_platform: string;
  confidence_score: number;
  detection_method: string;
  parser_executed: boolean;
  parser_version?: string | null;
  extracted_entities: PlatformEntity[];
  feature_flag_snapshot?: Record<string, unknown> | null;
  created_at?: string | null;
}

interface UsePlatformDetectionResult {
  data: PlatformDetectionData | null;
  loading: boolean;
  error: Error | null;
}

export function usePlatformDetection(jobId: string | null | undefined): UsePlatformDetectionResult {
  const [data, setData] = useState<PlatformDetectionData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!jobId) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    let isCancelled = false;
    setLoading(true);
    setError(null);

    const fetchPlatformDetection = async () => {
      try {
        const response = await fetch(`/api/v1/jobs/${jobId}/platform-detection`, {
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (isCancelled) return;

        if (!response.ok) {
          if (response.status === 404) {
            // No platform detection data available (expected for some jobs)
            setData(null);
            setLoading(false);
            return;
          }
          throw new Error(`Failed to fetch platform detection: ${response.status}`);
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        if (!isCancelled) {
          setError(err instanceof Error ? err : new Error("Unknown error"));
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    };

    fetchPlatformDetection();

    return () => {
      isCancelled = true;
    };
  }, [jobId]);

  return { data, loading, error };
}
