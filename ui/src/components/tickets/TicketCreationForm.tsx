'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Send, Eye, AlertCircle, FileText } from 'lucide-react';
import ticketApi from '@/lib/api/tickets';
import { TicketPlatform, ServiceNowPayload, JiraPayload, TemplateMetadata } from '@/types/tickets';
import toast from 'react-hot-toast';

interface TicketCreationFormProps {
  jobId: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export const TicketCreationForm: React.FC<TicketCreationFormProps> = ({
  jobId,
  onSuccess,
  onCancel,
}) => {
  const [platform, setPlatform] = useState<TicketPlatform>('servicenow');
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  
  // Template state
  const [templates, setTemplates] = useState<TemplateMetadata[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [templateVariables, setTemplateVariables] = useState<Record<string, any>>({});
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [useTemplate, setUseTemplate] = useState(false);

  // ServiceNow form fields
  const [snowFields, setSnowFields] = useState<ServiceNowPayload>({
    short_description: '',
    description: '',
    assignment_group: '',
    configuration_item: '',
    assigned_to: '',
    category: '',
    subcategory: '',
    priority: '3',
    state: '1',
  });

  // Jira form fields
  const [jiraFields, setJiraFields] = useState<JiraPayload>({
    project_key: '',
    issue_type: 'Incident',
    summary: '',
    description: '',
    assignee: '',
    labels: [],
    priority: 'Medium',
  });

  const [labelInput, setLabelInput] = useState('');
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Load templates when platform changes
  useEffect(() => {
    const loadTemplates = async () => {
      setTemplatesLoading(true);
      try {
        const response = await ticketApi.getTemplates(platform);
        setTemplates(response.templates);
      } catch (error) {
        console.error('Failed to load templates:', error);
      } finally {
        setTemplatesLoading(false);
      }
    };

    if (useTemplate) {
      loadTemplates();
    }
  }, [platform, useTemplate]);

  const handleSnowFieldChange = (field: keyof ServiceNowPayload, value: string) => {
    setSnowFields((prev) => ({ ...prev, [field]: value }));
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleJiraFieldChange = (field: keyof JiraPayload, value: any) => {
    setJiraFields((prev) => ({ ...prev, [field]: value }));
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleTemplateChange = (templateName: string) => {
    setSelectedTemplate(templateName);
    setTemplateVariables({});
    setValidationErrors({});
  };

  const handleTemplateVariableChange = (varName: string, value: string) => {
    setTemplateVariables((prev) => ({ ...prev, [varName]: value }));
  };

  const handleAddLabel = () => {
    if (labelInput.trim()) {
      setJiraFields((prev) => ({
        ...prev,
        labels: [...(prev.labels || []), labelInput.trim()],
      }));
      setLabelInput('');
    }
  };

  const handleRemoveLabel = (index: number) => {
    setJiraFields((prev) => ({
      ...prev,
      labels: (prev.labels || []).filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setValidationErrors({});

    try {
      if (useTemplate && selectedTemplate) {
        // Create from template
        await ticketApi.createFromTemplate({
          job_id: jobId,
          platform,
          template_name: selectedTemplate,
          variables: templateVariables,
          dry_run: dryRun,
        });
      } else {
        // Create from manual form
        const payload = platform === 'servicenow' ? snowFields : jiraFields;
        
        await ticketApi.createTicket({
          job_id: jobId,
          platform,
          payload,
          dry_run: dryRun,
        });
      }

      toast.success(
        dryRun
          ? 'Ticket preview created successfully'
          : `${platform === 'servicenow' ? 'ServiceNow' : 'Jira'} ticket created successfully`
      );

      onSuccess?.();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to create ticket';
      
      // Extract validation errors if present
      if (error.response?.data?.validation_errors) {
        const errors: Record<string, string> = {};
        error.response.data.validation_errors.forEach((err: any) => {
          errors[err.field] = err.message;
        });
        setValidationErrors(errors);
      }
      
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
          <Plus className="w-5 h-5 text-green-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Create New Ticket</h3>
          <p className="text-sm text-gray-500">Generate tickets for this RCA job</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Platform Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Platform <span className="text-red-500">*</span>
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setPlatform('servicenow')}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                platform === 'servicenow'
                  ? 'border-emerald-500 bg-emerald-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">🎫</span>
                <span className="font-semibold text-gray-900">ServiceNow</span>
              </div>
              <p className="text-xs text-gray-600">Create incident tickets with full ITSM workflow</p>
            </button>

            <button
              type="button"
              onClick={() => setPlatform('jira')}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                platform === 'jira'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">📊</span>
                <span className="font-semibold text-gray-900">Jira</span>
              </div>
              <p className="text-xs text-gray-600">Create issues with project tracking and labels</p>
            </button>
          </div>
        </div>

        {/* Template Toggle */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-indigo-600" />
              <div>
                <span className="block text-sm font-medium text-indigo-900">Use Template</span>
                <span className="block text-xs text-indigo-700 mt-0.5">
                  Create ticket from a pre-configured template with variable substitution
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={useTemplate}
              onChange={(e) => setUseTemplate(e.target.checked)}
              className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500"
            />
          </label>
        </div>

        {/* Template Selection */}
        {useTemplate && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Template <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedTemplate}
                onChange={(e) => handleTemplateChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required={useTemplate}
                disabled={templatesLoading}
              >
                <option value="">
                  {templatesLoading ? 'Loading templates...' : '-- Select a template --'}
                </option>
                {templates.map((template) => (
                  <option key={template.name} value={template.name}>
                    {template.name} ({template.field_count} fields)
                  </option>
                ))}
              </select>
            </div>

            {/* Template Variables */}
            {selectedTemplate && templates.find((t) => t.name === selectedTemplate) && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-3">Template Variables</h4>
                {(() => {
                  const template = templates.find((t) => t.name === selectedTemplate);
                  if (!template || template.required_variables.length === 0) {
                    return (
                      <p className="text-sm text-gray-600">This template has no required variables.</p>
                    );
                  }
                  return (
                    <div className="space-y-3">
                      {template.required_variables.map((varName) => (
                        <div key={varName}>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            {varName} <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="text"
                            value={templateVariables[varName] || ''}
                            onChange={(e) => handleTemplateVariableChange(varName, e.target.value)}
                            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                              validationErrors[varName]
                                ? 'border-red-300 focus:ring-red-500'
                                : 'border-gray-300 focus:ring-indigo-500'
                            }`}
                            placeholder={`Enter ${varName}`}
                            required
                          />
                          {validationErrors[varName] && (
                            <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                              <AlertCircle className="w-4 h-4" />
                              {validationErrors[varName]}
                            </p>
                          )}
                        </div>
                      ))}
                      {template.description && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <p className="text-sm text-gray-600">{template.description}</p>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {/* Dry Run Toggle */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div className="flex items-center gap-3">
              <Eye className="w-5 h-5 text-purple-600" />
              <div>
                <span className="block text-sm font-medium text-purple-900">Preview Mode (Dry Run)</span>
                <span className="block text-xs text-purple-700 mt-0.5">
                  Test ticket creation without actually creating it in the external system
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
            />
          </label>
        </div>

        {/* ServiceNow Fields */}
        {!useTemplate && platform === 'servicenow' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Short Description <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={snowFields.short_description}
                  onChange={(e) => handleSnowFieldChange('short_description', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                    validationErrors.short_description
                      ? 'border-red-300 focus:ring-red-500'
                      : 'border-gray-300 focus:ring-emerald-500'
                  }`}
                  placeholder="Brief summary of the incident"
                  required
                />
                {validationErrors.short_description && (
                  <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {validationErrors.short_description}
                  </p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={snowFields.description}
                  onChange={(e) => handleSnowFieldChange('description', e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Detailed incident description"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Assignment Group</label>
                <input
                  type="text"
                  value={snowFields.assignment_group}
                  onChange={(e) => handleSnowFieldChange('assignment_group', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g., IT Support"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Assigned To</label>
                <input
                  type="text"
                  value={snowFields.assigned_to}
                  onChange={(e) => handleSnowFieldChange('assigned_to', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="User ID or email"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Configuration Item</label>
                <input
                  type="text"
                  value={snowFields.configuration_item}
                  onChange={(e) => handleSnowFieldChange('configuration_item', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="CI name or ID"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <input
                  type="text"
                  value={snowFields.category}
                  onChange={(e) => handleSnowFieldChange('category', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g., Software"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subcategory</label>
                <input
                  type="text"
                  value={snowFields.subcategory}
                  onChange={(e) => handleSnowFieldChange('subcategory', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g., Application Error"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                <select
                  value={snowFields.priority}
                  onChange={(e) => handleSnowFieldChange('priority', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="1">1 - Critical</option>
                  <option value="2">2 - High</option>
                  <option value="3">3 - Moderate</option>
                  <option value="4">4 - Low</option>
                  <option value="5">5 - Planning</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">State</label>
                <select
                  value={snowFields.state}
                  onChange={(e) => handleSnowFieldChange('state', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="1">New</option>
                  <option value="2">In Progress</option>
                  <option value="3">On Hold</option>
                  <option value="6">Resolved</option>
                  <option value="7">Closed</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Jira Fields */}
        {!useTemplate && platform === 'jira' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Project Key <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={jiraFields.project_key}
                  onChange={(e) => handleJiraFieldChange('project_key', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                    validationErrors.project_key
                      ? 'border-red-300 focus:ring-red-500'
                      : 'border-gray-300 focus:ring-blue-500'
                  }`}
                  placeholder="e.g., PROJ"
                  required
                />
                {validationErrors.project_key && (
                  <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {validationErrors.project_key}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Issue Type</label>
                <select
                  value={jiraFields.issue_type}
                  onChange={(e) => handleJiraFieldChange('issue_type', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Incident">Incident</option>
                  <option value="Bug">Bug</option>
                  <option value="Task">Task</option>
                  <option value="Story">Story</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Summary <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={jiraFields.summary}
                  onChange={(e) => handleJiraFieldChange('summary', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                    validationErrors.summary
                      ? 'border-red-300 focus:ring-red-500'
                      : 'border-gray-300 focus:ring-blue-500'
                  }`}
                  placeholder="Brief issue summary"
                  required
                />
                {validationErrors.summary && (
                  <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {validationErrors.summary}
                  </p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={jiraFields.description}
                  onChange={(e) => handleJiraFieldChange('description', e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Detailed issue description"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Assignee</label>
                <input
                  type="text"
                  value={jiraFields.assignee as string}
                  onChange={(e) => handleJiraFieldChange('assignee', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Username or email"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                <select
                  value={jiraFields.priority as string}
                  onChange={(e) => handleJiraFieldChange('priority', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Highest">Highest</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                  <option value="Lowest">Lowest</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Labels</label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={labelInput}
                    onChange={(e) => setLabelInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddLabel();
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Add label and press Enter"
                  />
                  <button
                    type="button"
                    onClick={handleAddLabel}
                    className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                  >
                    Add
                  </button>
                </div>
                {jiraFields.labels && jiraFields.labels.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {jiraFields.labels.map((label, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                      >
                        {label}
                        <button
                          type="button"
                          onClick={() => handleRemoveLabel(index)}
                          className="hover:text-blue-900"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Automatic Field Population</p>
            <p>
              Empty fields will be automatically populated with defaults from the RCA job context and your
              environment configuration when the ticket is created.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {dryRun ? (
              <>
                <Eye className="w-4 h-4" />
                {loading ? 'Creating Preview...' : 'Preview Ticket'}
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                {loading ? 'Creating...' : 'Create Ticket'}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default TicketCreationForm;
