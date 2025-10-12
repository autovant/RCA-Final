'use client';

import React from 'react';
import { X, ExternalLink, Calendar, User, Tag, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { Ticket } from '@/types/tickets';
import {
  getStatusConfig,
  getPlatformConfig,
  formatDate,
  formatRelativeTime,
} from '@/lib/utils/ticketUtils';

interface TicketDetailViewProps {
  ticket: Ticket;
  onClose: () => void;
}

export const TicketDetailView: React.FC<TicketDetailViewProps> = ({ ticket, onClose }) => {
  const statusConfig = getStatusConfig(ticket.status);
  const platformConfig = getPlatformConfig(ticket.platform);

  const renderMetadataField = (label: string, value: string | undefined | null) => {
    if (!value) return null;
    return (
      <div className="flex justify-between items-start py-2 border-b border-gray-100 last:border-0">
        <span className="text-sm font-medium text-gray-600">{label}:</span>
        <span className="text-sm text-gray-900 text-right max-w-md">{value}</span>
      </div>
    );
  };

  const renderJiraMetadata = () => {
    if (ticket.platform !== 'jira' || !ticket.metadata) return null;

    return (
      <>
        {renderMetadataField('Project Key', ticket.metadata.project_key)}
        {renderMetadataField('Issue Type', ticket.metadata.issue_type)}
        {renderMetadataField('Priority', ticket.metadata.priority)}
        {renderMetadataField('Assignee', ticket.metadata.assignee)}
        {ticket.metadata.labels && ticket.metadata.labels.length > 0 && (
          <div className="flex justify-between items-start py-2 border-b border-gray-100">
            <span className="text-sm font-medium text-gray-600">Labels:</span>
            <div className="flex flex-wrap gap-1 justify-end max-w-md">
              {ticket.metadata.labels.map((label: string, index: number) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}
        {renderMetadataField('ServiceNow Reference', ticket.metadata.servicenow_incident_id)}
      </>
    );
  };

  const renderServiceNowMetadata = () => {
    if (ticket.platform !== 'servicenow' || !ticket.metadata) return null;

    return (
      <>
        {renderMetadataField('Assignment Group', ticket.metadata.assignment_group)}
        {renderMetadataField('Assigned To', ticket.metadata.assigned_to)}
        {renderMetadataField('Configuration Item', ticket.metadata.configuration_item)}
        {renderMetadataField('Category', ticket.metadata.category)}
        {renderMetadataField('Subcategory', ticket.metadata.subcategory)}
        {renderMetadataField('Priority', ticket.metadata.priority)}
        {renderMetadataField('State', ticket.metadata.state)}
      </>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{platformConfig.icon}</span>
            <div>
              <h2 className="text-xl font-bold text-white">Ticket Details</h2>
              <p className="text-sm text-blue-100 font-mono">{ticket.ticket_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-blue-800 p-2 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Status & Platform */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <Tag className="w-4 h-4 text-gray-600" />
                <span className="text-xs font-medium text-gray-600 uppercase">Platform</span>
              </div>
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${platformConfig.bgColor} ${platformConfig.color}`}
              >
                <span>{platformConfig.icon}</span>
                {platformConfig.label}
              </span>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="w-4 h-4 text-gray-600" />
                <span className="text-xs font-medium text-gray-600 uppercase">Status</span>
              </div>
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${statusConfig.bgColor} ${statusConfig.color}`}
              >
                <span>{statusConfig.icon}</span>
                {statusConfig.label}
              </span>
            </div>
          </div>

          {/* Preview Mode Alert */}
          {ticket.dry_run && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-semibold text-purple-900 mb-1">Preview Mode</h4>
                <p className="text-sm text-purple-800">
                  This ticket was created in preview mode and does not exist in the external ITSM system.
                </p>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {ticket.metadata?.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-semibold text-red-900 mb-1">Error</h4>
                <p className="text-sm text-red-800">{ticket.metadata.error}</p>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-gray-600" />
                <span className="text-sm font-medium text-gray-700">Created</span>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">{formatRelativeTime(ticket.created_at)}</p>
                <p className="text-xs text-gray-500">{formatDate(ticket.created_at)}</p>
              </div>
            </div>
            {ticket.updated_at && (
              <div className="flex items-center justify-between pt-3 border-t border-gray-200">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">Last Updated</span>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">{formatRelativeTime(ticket.updated_at)}</p>
                  <p className="text-xs text-gray-500">{formatDate(ticket.updated_at)}</p>
                </div>
              </div>
            )}
          </div>

          {/* Metadata */}
          {ticket.metadata && (
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Tag className="w-4 h-4" />
                Ticket Metadata
              </h4>
              <div className="space-y-1">
                {renderServiceNowMetadata()}
                {renderJiraMetadata()}
              </div>
            </div>
          )}

          {/* External Link */}
          {ticket.url && !ticket.dry_run && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <a
                href={ticket.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between group"
              >
                <div>
                  <h4 className="text-sm font-semibold text-blue-900 mb-1 flex items-center gap-2">
                    <ExternalLink className="w-4 h-4" />
                    View in {platformConfig.label}
                  </h4>
                  <p className="text-xs text-blue-700">Open this ticket in the external ITSM system</p>
                </div>
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                  <ExternalLink className="w-5 h-5 text-blue-600" />
                </div>
              </a>
            </div>
          )}

          {/* Job Reference */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-4 h-4 text-gray-600" />
              <span className="text-xs font-medium text-gray-600 uppercase">RCA Job Reference</span>
            </div>
            <p className="font-mono text-sm text-gray-900">{ticket.job_id}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TicketDetailView;
