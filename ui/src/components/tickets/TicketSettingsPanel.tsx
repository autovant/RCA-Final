'use client';

import React, { useEffect, useId, useState } from 'react';
import { Settings, Save, CheckCircle2, Info } from 'lucide-react';
import { useTicketStore } from '@/store/ticketStore';
import { Alert, Button, Card } from '@/components/ui';

export const TicketSettingsPanel: React.FC = () => {
  const { toggleState, loading, loadToggleState, updateToggleState } = useTicketStore();

  const [localState, setLocalState] = useState({
    servicenow_enabled: false,
    jira_enabled: false,
    dual_mode: false,
  });

  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const servicenowTitleId = useId();
  const servicenowToggleId = useId();
  const jiraTitleId = useId();
  const jiraToggleId = useId();
  const dualModeTitleId = useId();
  const dualModeToggleId = useId();

  useEffect(() => {
    loadToggleState();
  }, [loadToggleState]);

  useEffect(() => {
    if (toggleState) {
      setLocalState({
        servicenow_enabled: toggleState.servicenow_enabled,
        jira_enabled: toggleState.jira_enabled,
        dual_mode: toggleState.dual_mode,
      });
    }
  }, [toggleState]);

  const handleToggleChange = (field: keyof typeof localState, value: boolean) => {
    setLocalState((prev) => ({
      ...prev,
      [field]: value,
    }));
    setHasChanges(true);
    setSaveSuccess(false);
  };

  const handleSave = async () => {
    await updateToggleState(localState);
    setHasChanges(false);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const bothEnabled = localState.servicenow_enabled && localState.jira_enabled;

  return (
    <Card className="space-y-6 p-6 md:p-8">
      <div className="flex items-center gap-4 rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-fluent-blue-500/10 text-fluent-blue-200">
          <Settings className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-dark-text-primary">ITSM Integration Settings</h3>
          <p className="text-sm text-dark-text-secondary">Configure ServiceNow and Jira ticket creation.</p>
        </div>
      </div>

      <div className="space-y-6">
        <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-dark-text-primary">
                <span className="text-2xl">🎫</span>
                <h4 id={servicenowTitleId} className="text-base font-semibold">ServiceNow</h4>
              </div>
              <p className="text-sm text-dark-text-secondary">
                Automatically create incidents with assignment groups, configuration items, and priority
                mappings aligned to your ITSM workflow.
              </p>
              <div className="flex items-center gap-2 text-xs text-dark-text-tertiary">
                <Info className="h-3.5 w-3.5" />
                <span>Requires ServiceNow credentials in environment configuration.</span>
              </div>
            </div>
            <label
              htmlFor={servicenowToggleId}
              className="relative inline-flex h-7 w-12 cursor-pointer items-center rounded-full border border-dark-border/60 bg-dark-bg-primary transition focus-within:outline-none focus-within:ring-2 focus-within:ring-fluent-success/50"
            >
              <input
                id={servicenowToggleId}
                type="checkbox"
                className="peer sr-only"
                checked={localState.servicenow_enabled}
                onChange={() => handleToggleChange('servicenow_enabled', !localState.servicenow_enabled)}
                aria-labelledby={servicenowTitleId}
              />
              <span
                className={`absolute inset-0 rounded-full transition ${
                  localState.servicenow_enabled
                    ? 'border border-fluent-success/60 bg-fluent-success/30'
                    : 'border border-dark-border/60 bg-dark-bg-primary'
                }`}
              />
              <span
                className={`absolute left-1 top-1 h-5 w-5 rounded-full bg-dark-text-tertiary shadow-fluent transition-transform duration-200 ease-out ${
                  localState.servicenow_enabled ? 'translate-x-5 bg-fluent-success' : 'translate-x-0'
                }`}
              />
            </label>
          </div>
        </div>

        <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-dark-text-primary">
                <span className="text-2xl">📊</span>
                <h4 id={jiraTitleId} className="text-base font-semibold">Jira</h4>
              </div>
              <p className="text-sm text-dark-text-secondary">
                Create issues with customizable project keys, workflows, labels, and linked automation cues.
              </p>
              <div className="flex items-center gap-2 text-xs text-dark-text-tertiary">
                <Info className="h-3.5 w-3.5" />
                <span>Supports Jira Cloud and Server / Data Center editions.</span>
              </div>
            </div>
            <label
              htmlFor={jiraToggleId}
              className="relative inline-flex h-7 w-12 cursor-pointer items-center rounded-full border border-dark-border/60 bg-dark-bg-primary transition focus-within:outline-none focus-within:ring-2 focus-within:ring-fluent-blue-500/50"
            >
              <input
                id={jiraToggleId}
                type="checkbox"
                className="peer sr-only"
                checked={localState.jira_enabled}
                onChange={() => handleToggleChange('jira_enabled', !localState.jira_enabled)}
                aria-labelledby={jiraTitleId}
              />
              <span
                className={`absolute inset-0 rounded-full transition ${
                  localState.jira_enabled
                    ? 'border border-fluent-blue-500/60 bg-fluent-blue-500/30'
                    : 'border border-dark-border/60 bg-dark-bg-primary'
                }`}
              />
              <span
                className={`absolute left-1 top-1 h-5 w-5 rounded-full bg-dark-text-tertiary shadow-fluent transition-transform duration-200 ease-out ${
                  localState.jira_enabled ? 'translate-x-5 bg-fluent-blue-500' : 'translate-x-0'
                }`}
              />
            </label>
          </div>
        </div>

        {bothEnabled && (
          <div className="rounded-xl border border-fluent-blue-500/40 bg-fluent-blue-500/10 p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-dark-text-primary">
                  <span className="text-2xl">🔗</span>
                  <h4 id={dualModeTitleId} className="text-base font-semibold">Dual-Tracking Mode</h4>
                </div>
                <p className="text-sm text-dark-text-secondary">
                  Link Jira issues to their ServiceNow counterparts automatically for unified triage and status.
                </p>
                <div className="flex items-center gap-2 text-xs text-dark-text-tertiary">
                  <Info className="h-3.5 w-3.5" />
                  <span>Creates bidirectional references across both systems.</span>
                </div>
              </div>
              <label
                htmlFor={dualModeToggleId}
                className="relative inline-flex h-7 w-12 cursor-pointer items-center rounded-full border border-fluent-blue-500/40 bg-dark-bg-primary transition focus-within:outline-none focus-within:ring-2 focus-within:ring-fluent-blue-500/50"
              >
                <input
                  id={dualModeToggleId}
                  type="checkbox"
                  className="peer sr-only"
                  checked={localState.dual_mode}
                  onChange={() => handleToggleChange('dual_mode', !localState.dual_mode)}
                  aria-labelledby={dualModeTitleId}
                />
                <span
                  className={`absolute inset-0 rounded-full transition ${
                    localState.dual_mode
                      ? 'border border-fluent-blue-500/60 bg-fluent-blue-500/30'
                      : 'border border-fluent-blue-500/30 bg-dark-bg-primary'
                  }`}
                />
                <span
                  className={`absolute left-1 top-1 h-5 w-5 rounded-full bg-dark-text-tertiary shadow-fluent transition-transform duration-200 ease-out ${
                    localState.dual_mode ? 'translate-x-5 bg-fluent-blue-400' : 'translate-x-0'
                  }`}
                />
              </label>
            </div>
          </div>
        )}

        <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-5">
          <h5 className="text-sm font-semibold text-dark-text-primary">Active Configuration</h5>
          <div className="mt-3 space-y-2 text-sm text-dark-text-secondary">
            <div className="flex items-center justify-between">
              <span>ServiceNow Integration</span>
              <span
                className={`badge ${
                  localState.servicenow_enabled
                    ? 'border border-fluent-success/40 bg-fluent-success/15 text-green-300'
                    : 'border border-dark-border/60 bg-dark-bg-primary text-dark-text-tertiary'
                }`}
              >
                {localState.servicenow_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Jira Integration</span>
              <span
                className={`badge ${
                  localState.jira_enabled
                    ? 'border border-fluent-blue-500/40 bg-fluent-blue-500/15 text-fluent-blue-200'
                    : 'border border-dark-border/60 bg-dark-bg-primary text-dark-text-tertiary'
                }`}
              >
                {localState.jira_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            {bothEnabled && (
              <div className="flex items-center justify-between">
                <span>Dual-Tracking Mode</span>
                <span
                  className={`badge ${
                    localState.dual_mode
                      ? 'border border-fluent-blue-500/40 bg-fluent-blue-500/15 text-fluent-blue-200'
                      : 'border border-dark-border/60 bg-dark-bg-primary text-dark-text-tertiary'
                  }`}
                >
                  {localState.dual_mode ? 'Active' : 'Inactive'}
                </span>
              </div>
            )}
          </div>
        </div>

        {!localState.servicenow_enabled && !localState.jira_enabled && (
          <Alert variant="warning" title="No integrations enabled">
            Enable at least one integration to create tickets automatically. Tickets remain in preview mode when
            both integrations are disabled.
          </Alert>
        )}

        <div className="flex items-center justify-between border-t border-dark-border/60 pt-4">
          <div className="flex items-center gap-2 text-sm text-green-300">
            {saveSuccess && (
              <>
                <CheckCircle2 className="h-5 w-5" />
                <span>Settings saved successfully</span>
              </>
            )}
          </div>
          <Button
            onClick={handleSave}
            disabled={!hasChanges || loading}
            loading={loading}
            icon={<Save className="h-4 w-4" />}
          >
            {loading ? 'Saving…' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </Card>
  );
};

export default TicketSettingsPanel;
