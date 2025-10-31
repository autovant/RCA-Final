'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Send, Eye, AlertCircle, FileText } from 'lucide-react';
import ticketApi from '@/lib/api/tickets';
import { TicketPlatform, ServiceNowPayload, JiraPayload, TemplateMetadata } from '@/types/tickets';
import toast from 'react-hot-toast';
import { Button, Card } from '@/components/ui';

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
  const [templateVariables, setTemplateVariables] = useState<Record<string, string>>({});
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

  const handleJiraFieldChange = (
    field: keyof JiraPayload,
    value: JiraPayload[keyof JiraPayload]
  ) => {
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
    } catch (error) {
      const err = error as {
        response?: {
          data?: {
            detail?: string;
            validation_errors?: Array<{ field: string; message: string }>;
          };
        };
        message?: string;
      };
      const errorMessage =
        err.response?.data?.detail || err.message || 'Failed to create ticket';

      if (err.response?.data?.validation_errors) {
        const errors: Record<string, string> = {};
        err.response.data.validation_errors.forEach((validationError) => {
          errors[validationError.field] = validationError.message;
        });
        setValidationErrors(errors);
      }

      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const actionLabel = dryRun
    ? loading
      ? 'Creating Preview…'
      : 'Preview Ticket'
    : loading
    ? 'Creating…'
    : 'Create Ticket';

  return (
    <Card className="space-y-6 p-6 md:p-8">
      <div className="flex items-center gap-4 rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-fluent-success/10 text-fluent-success">
          <Plus className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-dark-text-primary">Create New Ticket</h3>
          <p className="text-sm text-dark-text-secondary">Generate tickets for this RCA job</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Platform Selection */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-dark-text-tertiary">
            Platform <span className="text-fluent-error">*</span>
          </label>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <button
              type="button"
              onClick={() => setPlatform('servicenow')}
              className={`rounded-xl border p-4 text-left transition-all ${
                platform === 'servicenow'
                  ? 'border-fluent-success/40 bg-fluent-success/10 shadow-fluent-lg'
                  : 'border-dark-border/70 bg-dark-bg-tertiary/60 hover:border-dark-border/40'
              }`}
            >
              <div className="flex items-center gap-2 text-dark-text-primary">
                <span className="text-2xl">🎫</span>
                <span className="font-semibold">ServiceNow</span>
              </div>
              <p className="mt-3 text-sm text-dark-text-secondary">
                Create incident tickets with full ITSM workflow.
              </p>
            </button>

            <button
              type="button"
              onClick={() => setPlatform('jira')}
              className={`rounded-xl border p-4 text-left transition-all ${
                platform === 'jira'
                  ? 'border-fluent-blue-500/40 bg-fluent-blue-500/10 shadow-fluent-lg'
                  : 'border-dark-border/70 bg-dark-bg-tertiary/60 hover:border-dark-border/40'
              }`}
            >
              <div className="flex items-center gap-2 text-dark-text-primary">
                <span className="text-2xl">📊</span>
                <span className="font-semibold">Jira</span>
              </div>
              <p className="mt-3 text-sm text-dark-text-secondary">
                Create issues with project tracking and labels.
              </p>
            </button>
          </div>
        </div>

        {/* Template Toggle */}
        <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-5">
          <label className="flex items-center justify-between gap-6 cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-fluent-blue-500/10 text-fluent-blue-200">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <span className="block text-sm font-semibold text-dark-text-primary">Use Template</span>
                <span className="block text-xs text-dark-text-secondary mt-0.5">
                  Create tickets from pre-configured blueprints with variable substitution.
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={useTemplate}
              onChange={(e) => setUseTemplate(e.target.checked)}
              className="h-5 w-5 rounded border-dark-border bg-dark-bg-tertiary text-fluent-blue-400 focus:ring-fluent-blue-500"
              aria-label="Toggle template usage"
            />
          </label>
        </div>

        {/* Template Selection */}
        {useTemplate && (
          <div className="space-y-4">
            <div>
              <label
                htmlFor="template-select"
                className="block text-sm font-semibold text-dark-text-secondary mb-2"
              >
                Select Template <span className="text-fluent-error">*</span>
              </label>
              <select
                value={selectedTemplate}
                onChange={(e) => handleTemplateChange(e.target.value)}
                id="template-select"
                className="input"
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
              <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-4">
                <h4 className="text-sm font-semibold text-dark-text-primary mb-3">Template Variables</h4>
                {(() => {
                  const template = templates.find((t) => t.name === selectedTemplate);
                  if (!template || template.required_variables.length === 0) {
                    return (
                      <p className="text-sm text-dark-text-secondary">This template has no required variables.</p>
                    );
                  }
                  return (
                    <div className="space-y-3">
                      {template.required_variables.map((varName) => (
                        <div key={varName}>
                          <label className="block text-sm font-medium text-dark-text-secondary mb-1">
                            {varName} <span className="text-fluent-error">*</span>
                          </label>
                          <input
                            type="text"
                            value={templateVariables[varName] || ''}
                            onChange={(e) => handleTemplateVariableChange(varName, e.target.value)}
                            className={`input ${
                              validationErrors[varName]
                                ? 'border-fluent-error focus:ring-fluent-error'
                                : 'border-dark-border focus:ring-fluent-blue-500'
                            }`}
                            placeholder={`Enter ${varName}`}
                            required
                          />
                          {validationErrors[varName] && (
                            <p className="mt-1 flex items-center gap-1 text-sm text-fluent-error">
                              <AlertCircle className="h-4 w-4" />
                              {validationErrors[varName]}
                            </p>
                          )}
                        </div>
                      ))}
                      {template.description && (
                        <div className="mt-4 border-t border-dark-border/60 pt-4">
                          <p className="text-sm text-dark-text-secondary">{template.description}</p>
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
        <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-5">
          <label className="flex items-center justify-between gap-6 cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-fluent-info/10 text-fluent-info">
                <Eye className="h-5 w-5" />
              </div>
              <div>
                <span className="block text-sm font-semibold text-dark-text-primary">
                  Preview Mode (Dry Run)
                </span>
                <span className="block text-xs text-dark-text-secondary mt-0.5">
                  Test ticket creation without sending it to the external ITSM platform.
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="h-5 w-5 rounded border-dark-border bg-dark-bg-tertiary text-fluent-info focus:ring-fluent-info"
              aria-label="Toggle dry run"
            />
          </label>
        </div>

        {/* ServiceNow Fields */}
        {!useTemplate && platform === 'servicenow' && (
          <div className="space-y-5 rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-5">
            <div>
              <h4 className="text-sm font-semibold text-dark-text-primary">ServiceNow Details</h4>
              <p className="text-xs text-dark-text-secondary">
                Map the incident context that will land in ServiceNow.
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2 space-y-2">
                <label
                  htmlFor="snow-short-description"
                  className="text-sm font-medium text-dark-text-secondary"
                >
                  Short Description <span className="text-fluent-error">*</span>
                </label>
                <input
                  id="snow-short-description"
                  type="text"
                  value={snowFields.short_description}
                  onChange={(e) => handleSnowFieldChange('short_description', e.target.value)}
                  className={`input ${
                    validationErrors.short_description
                      ? 'border-fluent-error focus:ring-fluent-error'
                      : ''
                  }`}
                  placeholder="Brief summary of the incident"
                  required
                />
                {validationErrors.short_description && (
                  <p className="flex items-center gap-1 text-sm text-fluent-error">
                    <AlertCircle className="h-4 w-4" />
                    {validationErrors.short_description}
                  </p>
                )}
              </div>

              <div className="md:col-span-2 space-y-2">
                <label
                  htmlFor="snow-description"
                  className="text-sm font-medium text-dark-text-secondary"
                >
                  Description
                </label>
                <textarea
                  id="snow-description"
                  value={snowFields.description}
                  onChange={(e) => handleSnowFieldChange('description', e.target.value)}
                  rows={4}
                  className="input min-h-[120px] resize-y"
                  placeholder="Detailed incident description"
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="snow-assignment-group"
                  className="text-sm font-medium text-dark-text-secondary"
                >
                  Assignment Group
                </label>
                <input
                  id="snow-assignment-group"
                  type="text"
                  value={snowFields.assignment_group}
                  onChange={(e) => handleSnowFieldChange('assignment_group', e.target.value)}
                  className="input"
                  placeholder="e.g., IT Support"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="snow-assigned-to" className="text-sm font-medium text-dark-text-secondary">
                  Assigned To
                </label>
                <input
                  id="snow-assigned-to"
                  type="text"
                  value={snowFields.assigned_to}
                  onChange={(e) => handleSnowFieldChange('assigned_to', e.target.value)}
                  className="input"
                  placeholder="User ID or email"
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="snow-configuration-item"
                  className="text-sm font-medium text-dark-text-secondary"
                >
                  Configuration Item
                </label>
                <input
                  id="snow-configuration-item"
                  type="text"
                  value={snowFields.configuration_item}
                  onChange={(e) => handleSnowFieldChange('configuration_item', e.target.value)}
                  className="input"
                  placeholder="CI name or ID"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="snow-category" className="text-sm font-medium text-dark-text-secondary">
                  Category
                </label>
                <input
                  id="snow-category"
                  type="text"
                  value={snowFields.category}
                  onChange={(e) => handleSnowFieldChange('category', e.target.value)}
                  className="input"
                  placeholder="e.g., Software"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="snow-subcategory" className="text-sm font-medium text-dark-text-secondary">
                  Subcategory
                </label>
                <input
                  id="snow-subcategory"
                  type="text"
                  value={snowFields.subcategory}
                  onChange={(e) => handleSnowFieldChange('subcategory', e.target.value)}
                  className="input"
                  placeholder="e.g., Application Error"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="snow-priority" className="text-sm font-medium text-dark-text-secondary">
                  Priority
                </label>
                <select
                  id="snow-priority"
                  value={snowFields.priority}
                  onChange={(e) => handleSnowFieldChange('priority', e.target.value)}
                  className="input"
                >
                  <option value="1">1 - Critical</option>
                  <option value="2">2 - High</option>
                  <option value="3">3 - Moderate</option>
                  <option value="4">4 - Low</option>
                  <option value="5">5 - Planning</option>
                </select>
              </div>

              <div className="space-y-2">
                <label htmlFor="snow-state" className="text-sm font-medium text-dark-text-secondary">
                  State
                </label>
                <select
                  id="snow-state"
                  value={snowFields.state}
                  onChange={(e) => handleSnowFieldChange('state', e.target.value)}
                  className="input"
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
          <div className="space-y-5 rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-5">
            <div>
              <h4 className="text-sm font-semibold text-dark-text-primary">Jira Details</h4>
              <p className="text-xs text-dark-text-secondary">
                Configure issue metadata for your engineering teams.
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label htmlFor="jira-project" className="text-sm font-medium text-dark-text-secondary">
                  Project Key <span className="text-fluent-error">*</span>
                </label>
                <input
                  id="jira-project"
                  type="text"
                  value={jiraFields.project_key}
                  onChange={(e) => handleJiraFieldChange('project_key', e.target.value)}
                  className={`input ${
                    validationErrors.project_key ? 'border-fluent-error focus:ring-fluent-error' : ''
                  }`}
                  placeholder="e.g., PROJ"
                  required
                />
                {validationErrors.project_key && (
                  <p className="flex items-center gap-1 text-sm text-fluent-error">
                    <AlertCircle className="h-4 w-4" />
                    {validationErrors.project_key}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label htmlFor="jira-issue-type" className="text-sm font-medium text-dark-text-secondary">
                  Issue Type
                </label>
                <select
                  id="jira-issue-type"
                  value={jiraFields.issue_type}
                  onChange={(e) => handleJiraFieldChange('issue_type', e.target.value)}
                  className="input"
                >
                  <option value="Incident">Incident</option>
                  <option value="Bug">Bug</option>
                  <option value="Task">Task</option>
                  <option value="Story">Story</option>
                </select>
              </div>

              <div className="md:col-span-2 space-y-2">
                <label htmlFor="jira-summary" className="text-sm font-medium text-dark-text-secondary">
                  Summary <span className="text-fluent-error">*</span>
                </label>
                <input
                  id="jira-summary"
                  type="text"
                  value={jiraFields.summary}
                  onChange={(e) => handleJiraFieldChange('summary', e.target.value)}
                  className={`input ${
                    validationErrors.summary ? 'border-fluent-error focus:ring-fluent-error' : ''
                  }`}
                  placeholder="Brief issue summary"
                  required
                />
                {validationErrors.summary && (
                  <p className="flex items-center gap-1 text-sm text-fluent-error">
                    <AlertCircle className="h-4 w-4" />
                    {validationErrors.summary}
                  </p>
                )}
              </div>

              <div className="md:col-span-2 space-y-2">
                <label htmlFor="jira-description" className="text-sm font-medium text-dark-text-secondary">
                  Description
                </label>
                <textarea
                  id="jira-description"
                  value={jiraFields.description}
                  onChange={(e) => handleJiraFieldChange('description', e.target.value)}
                  rows={4}
                  className="input min-h-[120px] resize-y"
                  placeholder="Detailed issue description"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="jira-assignee" className="text-sm font-medium text-dark-text-secondary">
                  Assignee
                </label>
                <input
                  id="jira-assignee"
                  type="text"
                  value={jiraFields.assignee as string}
                  onChange={(e) => handleJiraFieldChange('assignee', e.target.value)}
                  className="input"
                  placeholder="Username or email"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="jira-priority" className="text-sm font-medium text-dark-text-secondary">
                  Priority
                </label>
                <select
                  id="jira-priority"
                  value={jiraFields.priority as string}
                  onChange={(e) => handleJiraFieldChange('priority', e.target.value)}
                  className="input"
                >
                  <option value="Highest">Highest</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                  <option value="Lowest">Lowest</option>
                </select>
              </div>

              <div className="md:col-span-2 space-y-3">
                <label htmlFor="jira-label-input" className="text-sm font-medium text-dark-text-secondary">
                  Labels
                </label>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <input
                    id="jira-label-input"
                    type="text"
                    value={labelInput}
                    onChange={(e) => setLabelInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddLabel();
                      }
                    }}
                    className="input flex-1"
                    placeholder="Add label and press Enter"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={handleAddLabel}
                  >
                    Add
                  </Button>
                </div>
                {jiraFields.labels && jiraFields.labels.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {jiraFields.labels.map((label, index) => (
                      <span
                        key={index}
                        className="badge bg-fluent-blue-500/10 text-fluent-blue-200 border border-fluent-blue-500/30"
                      >
                        {label}
                        <button
                          type="button"
                          onClick={() => handleRemoveLabel(index)}
                          className="ml-1 text-xs text-dark-text-tertiary hover:text-dark-text-primary"
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
        <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-fluent-info mt-0.5 flex-shrink-0" />
            <div className="text-sm text-dark-text-secondary">
              <p className="font-semibold text-dark-text-primary">Automatic Field Population</p>
              <p className="mt-1">
                Empty fields pull from the RCA job context and environment configuration before submission.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 border-t border-dark-border/60 pt-4">
          {onCancel && (
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button
            type="submit"
            loading={loading}
            icon={dryRun ? <Eye className="h-4 w-4" /> : <Send className="h-4 w-4" />}
          >
            {actionLabel}
          </Button>
        </div>
      </form>
    </Card>
  );
};

export default TicketCreationForm;
