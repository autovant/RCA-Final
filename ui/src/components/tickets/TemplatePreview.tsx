/**
 * TemplatePreview Component
 * 
 * Displays template metadata including description, required variables,
 * and field mapping information to help users understand what the template will generate.
 */

import React from 'react';
import { FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { TemplateMetadata } from '@/types/tickets';

interface TemplatePreviewProps {
  template: TemplateMetadata;
  variables?: Record<string, string>;
  className?: string;
}

export const TemplatePreview: React.FC<TemplatePreviewProps> = ({
  template,
  variables = {},
  className = '',
}) => {
  const missingVariables = template.required_variables.filter(
    (varName) => !variables[varName] || variables[varName].trim() === ''
  );

  const isComplete = missingVariables.length === 0;

  return (
    <div className={`card ${className}`}>
      <div className="flex items-center gap-4 border-b border-dark-border/60 bg-dark-bg-tertiary/60 px-4 py-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-fluent-blue-500/10 text-fluent-blue-200">
          <FileText className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-dark-text-primary">{template.name}</h3>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-dark-text-tertiary">
            <span>
              Platform: <span className="font-medium text-dark-text-secondary">{template.platform}</span>
            </span>
            <span>•</span>
            <span>{template.field_count} field{template.field_count !== 1 ? 's' : ''}</span>
          </div>
        </div>
        {isComplete ? (
          <div className="flex items-center gap-2 text-fluent-success">
            <CheckCircle className="h-5 w-5" />
            <span className="text-sm font-medium">Ready</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-fluent-warning">
            <AlertCircle className="h-5 w-5" />
            <span className="text-sm font-medium">{missingVariables.length} missing</span>
          </div>
        )}
      </div>

      <div className="space-y-4 p-4">
        {template.description && (
          <div>
            <h4 className="text-sm font-semibold text-dark-text-primary">Description</h4>
            <p className="mt-1 text-sm text-dark-text-secondary leading-relaxed">{template.description}</p>
          </div>
        )}

        {template.required_variables.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-dark-text-primary">Required Variables</h4>
            <div className="mt-2 space-y-2">
              {template.required_variables.map((varName) => {
                const rawValue = variables[varName] ?? '';
                const value = typeof rawValue === 'string' ? rawValue.trim() : '';
                const hasValue = value.length > 0;
                return (
                  <div
                    key={varName}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 ${
                      hasValue
                        ? 'border-fluent-success/40 bg-fluent-success/10 text-green-200'
                        : 'border-dark-border/60 bg-dark-bg-tertiary/80 text-dark-text-secondary'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {hasValue ? (
                        <CheckCircle className="h-4 w-4" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-dark-text-tertiary" />
                      )}
                      <span className="font-mono text-sm">{varName}</span>
                    </div>
                    {hasValue ? (
                      <span className="truncate text-xs text-dark-text-primary">
                        {value.length > 30 ? `${value.substring(0, 30)}…` : value}
                      </span>
                    ) : (
                      <span className="text-xs italic text-dark-text-tertiary">Not set</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="rounded-lg border border-fluent-blue-500/30 bg-fluent-blue-500/10 p-3 text-sm text-dark-text-primary">
          <div className="flex items-start gap-2">
            <FileText className="h-4 w-4 text-fluent-blue-200" />
            <div>
              <p>
                This template generates <strong>{template.field_count}</strong> field
                {template.field_count !== 1 ? 's' : ''} in the outgoing ticket.
              </p>
              {isComplete ? (
                <p className="mt-1 text-xs text-dark-text-secondary">
                  All required variables are provided. The ticket is ready to submit.
                </p>
              ) : (
                <p className="mt-1 text-xs text-dark-text-secondary">
                  Provide {missingVariables.length} missing value
                  {missingVariables.length !== 1 ? 's' : ''} to enable this template.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemplatePreview;
