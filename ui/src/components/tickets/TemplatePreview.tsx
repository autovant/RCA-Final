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
  variables?: Record<string, any>;
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
    <div className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
            <FileText className="w-5 h-5 text-indigo-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-gray-900">{template.name}</h3>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-xs text-gray-500">
                Platform: <span className="font-medium text-gray-700">{template.platform}</span>
              </span>
              <span className="text-xs text-gray-500">•</span>
              <span className="text-xs text-gray-500">
                {template.field_count} field{template.field_count !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
          {isComplete ? (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="w-5 h-5" />
              <span className="text-sm font-medium">Ready</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-amber-600">
              <AlertCircle className="w-5 h-5" />
              <span className="text-sm font-medium">{missingVariables.length} missing</span>
            </div>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Description */}
        {template.description && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Description</h4>
            <p className="text-sm text-gray-600 leading-relaxed">{template.description}</p>
          </div>
        )}

        {/* Required Variables */}
        {template.required_variables.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Required Variables</h4>
            <div className="space-y-2">
              {template.required_variables.map((varName) => {
                const hasValue = variables[varName] && variables[varName].trim() !== '';
                return (
                  <div
                    key={varName}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg ${
                      hasValue ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {hasValue ? (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-gray-400" />
                      )}
                      <span className="text-sm font-mono text-gray-700">{varName}</span>
                    </div>
                    {hasValue ? (
                      <span className="text-xs text-green-700 bg-green-100 px-2 py-1 rounded">
                        {String(variables[varName]).length > 30
                          ? `${String(variables[varName]).substring(0, 30)}...`
                          : String(variables[varName])}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500 italic">Not set</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Field Count Summary */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <FileText className="w-4 h-4 text-indigo-600 mt-0.5" />
            <div>
              <p className="text-sm text-indigo-900">
                This template will generate a ticket with <strong>{template.field_count} field{template.field_count !== 1 ? 's' : ''}</strong>.
              </p>
              {isComplete ? (
                <p className="text-xs text-indigo-700 mt-1">
                  All required variables are provided. The ticket is ready to be created.
                </p>
              ) : (
                <p className="text-xs text-indigo-700 mt-1">
                  Please provide the {missingVariables.length} missing variable{missingVariables.length !== 1 ? 's' : ''} to continue.
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
