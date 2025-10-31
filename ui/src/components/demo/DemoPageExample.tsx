/**
 * Example usage page showing how to integrate demo features with API
 */

'use client';

import React, { useState } from 'react';
import { useDemoFeedback, useDemoAnalytics, useDemoShare } from '@/hooks/useDemoAPI';
import { Star, Send, Share2, Download, Check, AlertCircle } from 'lucide-react';

interface DemoPageProps {
  demoId: string;
  demoTitle: string;
  demoConfig: Record<string, unknown>;
}

export default function DemoPage({ demoId, demoTitle, demoConfig }: DemoPageProps) {
  // Hooks
  const { submitFeedback, isSubmitting, error: feedbackError, submitted } = useDemoFeedback(demoId);
  const { trackInteraction, trackExport } = useDemoAnalytics(demoId);
  const { createShare, shareUrl, isSharing, error: shareError } = useDemoShare();

  // Local state
  const [rating, setRating] = useState(0);
  const [comments, setComments] = useState('');
  const [copied, setCopied] = useState(false);

  // Handlers
  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await submitFeedback({
      rating,
      comments: comments.trim() || undefined,
    });
  };

  const handleShare = async () => {
    await createShare({
      demo_config: demoConfig,
      title: demoTitle,
      description: `Shared demo: ${demoTitle}`,
      expires_hours: 24,
    });
  };

  const handleExport = (format: 'json' | 'csv') => {
    trackExport(format);
    
    // Export logic
    const dataStr = format === 'json' 
      ? JSON.stringify(demoConfig, null, 2)
      : convertToCSV(demoConfig);
    
    const blob = new Blob([dataStr], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${demoTitle}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyShareUrl = () => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl p-6 space-y-8">
      {/* Demo Content */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold mb-4">{demoTitle}</h1>
        <div 
          className="prose max-w-none"
          onClick={(e) => {
            const target = e.target as HTMLElement;
            if (target.id) {
              trackInteraction('click', { element_id: target.id });
            }
          }}
        >
          {/* Your demo content here */}
          <p>Demo content goes here...</p>
        </div>
      </div>

      {/* Export & Share Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => handleExport('json')}
          className="flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-white hover:bg-green-700"
        >
          <Download className="h-4 w-4" />
          Export JSON
        </button>
        
        <button
          onClick={() => handleExport('csv')}
          className="flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-white hover:bg-green-700"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </button>
        
        <button
          onClick={handleShare}
          disabled={isSharing}
          className="flex items-center gap-2 rounded-md bg-purple-600 px-4 py-2 text-white hover:bg-purple-700 disabled:opacity-50"
        >
          <Share2 className="h-4 w-4" />
          {isSharing ? 'Creating...' : 'Share'}
        </button>
      </div>

      {/* Share URL Display */}
      {shareUrl && (
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
          <p className="mb-2 text-sm font-medium text-purple-900">
            Shareable Link (expires in 24 hours):
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={shareUrl}
              readOnly
              className="flex-1 rounded border border-purple-300 bg-white px-3 py-2 text-sm"
            />
            <button
              onClick={handleCopyShareUrl}
              className="flex items-center gap-2 rounded-md bg-purple-600 px-3 py-2 text-white hover:bg-purple-700"
            >
              {copied ? <Check className="h-4 w-4" /> : <Share2 className="h-4 w-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>
      )}

      {shareError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            <span>{shareError}</span>
          </div>
        </div>
      )}

      {/* Feedback Form */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Share Your Feedback</h2>
        
        {submitted ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-center">
            <Check className="mx-auto mb-3 h-12 w-12 text-green-600" />
            <h3 className="mb-2 text-lg font-semibold text-green-900">Thank You!</h3>
            <p className="text-green-700">
              Your feedback has been submitted successfully. We appreciate your input!
            </p>
          </div>
        ) : (
          <form onSubmit={handleFeedbackSubmit} className="space-y-4">
            {/* Rating */}
            <div>
              <label className="mb-2 block text-sm font-medium">
                Rate this demo
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    className="focus:outline-none"
                  >
                    <Star
                      className={`h-8 w-8 ${
                        star <= rating
                          ? 'fill-yellow-400 text-yellow-400'
                          : 'text-gray-300'
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Comments */}
            <div>
              <label htmlFor="comments" className="mb-2 block text-sm font-medium">
                Comments (optional)
              </label>
              <textarea
                id="comments"
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                rows={4}
                className="w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="Tell us what you think..."
              />
            </div>

            {feedbackError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {feedbackError}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || rating === 0}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-4 w-4" />
              {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

// Helper function to convert data to CSV
function convertToCSV(data: Record<string, unknown>): string {
  const headers = Object.keys(data);
  const values = Object.values(data);
  
  return [
    headers.join(','),
    values.map(v => JSON.stringify(v)).join(',')
  ].join('\n');
}
