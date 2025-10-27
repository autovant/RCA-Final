/**
 * Hooks for using the Demo API features
 */

import { useState, useCallback, useEffect } from 'react';
import { demoAPI, type DemoFeedback, type ShareDemoRequest } from '@/lib/api/demoAPI';

/**
 * Hook for submitting demo feedback
 */
export function useDemoFeedback(demoId: string) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const submitFeedback = useCallback(async (feedback: Omit<DemoFeedback, 'demo_id'>) => {
    setIsSubmitting(true);
    setError(null);

    try {
      await demoAPI.submitFeedback({
        demo_id: demoId,
        ...feedback,
      });
      setSubmitted(true);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, [demoId]);

  const reset = useCallback(() => {
    setSubmitted(false);
    setError(null);
  }, []);

  return {
    submitFeedback,
    isSubmitting,
    error,
    submitted,
    reset,
  };
}

/**
 * Hook for tracking demo analytics
 */
export function useDemoAnalytics(demoId: string) {
  useEffect(() => {
    // Track view on mount
    demoAPI.trackView(demoId);
  }, [demoId]);

  const trackInteraction = useCallback((interactionType: string, metadata?: Record<string, unknown>) => {
    demoAPI.trackInteraction(demoId, interactionType, metadata);
  }, [demoId]);

  const trackExport = useCallback((format: string) => {
    demoAPI.trackExport(demoId, format);
  }, [demoId]);

  return {
    trackInteraction,
    trackExport,
  };
}

/**
 * Hook for creating shareable demo links
 */
export function useDemoShare() {
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [isSharing, setIsSharing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createShare = useCallback(async (request: ShareDemoRequest) => {
    setIsSharing(true);
    setError(null);

    try {
      const response = await demoAPI.createShare(request);
      const fullUrl = `${window.location.origin}/demo/shared/${response.share_id}`;
      setShareUrl(fullUrl);
      return fullUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create share link');
      return null;
    } finally {
      setIsSharing(false);
    }
  }, []);

  const reset = useCallback(() => {
    setShareUrl(null);
    setError(null);
  }, []);

  return {
    createShare,
    shareUrl,
    isSharing,
    error,
    reset,
  };
}

/**
 * Hook for fetching demo feedback summary
 */
export function useFeedbackSummary(demoId: string) {
  const [summary, setSummary] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await demoAPI.getFeedbackSummary(demoId);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch summary');
    } finally {
      setIsLoading(false);
    }
  }, [demoId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return {
    summary,
    isLoading,
    error,
    refetch: fetchSummary,
  };
}

/**
 * Hook for fetching demo analytics summary
 */
export function useAnalyticsSummary(demoId: string, hours: number = 24) {
  const [summary, setSummary] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await demoAPI.getAnalyticsSummary(demoId, hours);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics');
    } finally {
      setIsLoading(false);
    }
  }, [demoId, hours]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return {
    summary,
    isLoading,
    error,
    refetch: fetchSummary,
  };
}
