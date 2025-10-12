'use client';

import React, { useEffect, useState } from 'react';
import { Settings, Save, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { useTicketStore } from '@/store/ticketStore';

export const TicketSettingsPanel: React.FC = () => {
  const { toggleState, loading, loadToggleState, updateToggleState } = useTicketStore();
  
  const [localState, setLocalState] = useState({
    servicenow_enabled: false,
    jira_enabled: false,
    dual_mode: false,
  });

  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

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
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
          <Settings className="w-5 h-5 text-blue-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">ITSM Integration Settings</h3>
          <p className="text-sm text-gray-500">Configure ServiceNow and Jira ticket creation</p>
        </div>
      </div>

      <div className="space-y-6">
        {/* ServiceNow Toggle */}
        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">🎫</span>
                <h4 className="text-base font-semibold text-gray-900">ServiceNow</h4>
              </div>
              <p className="text-sm text-gray-600 mb-3">
                Automatically create incidents in ServiceNow with full field mapping including assignment
                groups, configuration items, and priority levels.
              </p>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Info className="w-3.5 h-3.5" />
                <span>Requires ServiceNow credentials in environment configuration</span>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={localState.servicenow_enabled}
                onChange={(e) => handleToggleChange('servicenow_enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>

        {/* Jira Toggle */}
        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">📊</span>
                <h4 className="text-base font-semibold text-gray-900">Jira</h4>
              </div>
              <p className="text-sm text-gray-600 mb-3">
                Create issues in Jira with customizable project keys, issue types, priorities, labels, and
                component assignments for comprehensive project tracking.
              </p>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Info className="w-3.5 h-3.5" />
                <span>Supports both Jira Cloud and Server/Data Center editions</span>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={localState.jira_enabled}
                onChange={(e) => handleToggleChange('jira_enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>

        {/* Dual Mode Toggle */}
        {bothEnabled && (
          <div className="border-2 border-blue-200 bg-blue-50 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">🔗</span>
                  <h4 className="text-base font-semibold text-blue-900">Dual-Tracking Mode</h4>
                </div>
                <p className="text-sm text-blue-800 mb-3">
                  When enabled, Jira issues will automatically reference their linked ServiceNow incidents,
                  creating a unified tracking experience across both platforms.
                </p>
                <div className="flex items-center gap-2 text-xs text-blue-700">
                  <Info className="w-3.5 h-3.5" />
                  <span>Creates bidirectional references for complete incident tracking</span>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer ml-4">
                <input
                  type="checkbox"
                  checked={localState.dual_mode}
                  onChange={(e) => handleToggleChange('dual_mode', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-blue-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-blue-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>
        )}

        {/* Current Configuration Summary */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h5 className="text-sm font-semibold text-gray-900 mb-3">Active Configuration</h5>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">ServiceNow Integration:</span>
              <span className={`font-medium ${localState.servicenow_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                {localState.servicenow_enabled ? '✓ Enabled' : '✗ Disabled'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Jira Integration:</span>
              <span className={`font-medium ${localState.jira_enabled ? 'text-green-600' : 'text-gray-400'}`}>
                {localState.jira_enabled ? '✓ Enabled' : '✗ Disabled'}
              </span>
            </div>
            {bothEnabled && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Dual-Tracking Mode:</span>
                <span className={`font-medium ${localState.dual_mode ? 'text-blue-600' : 'text-gray-400'}`}>
                  {localState.dual_mode ? '✓ Active' : '✗ Inactive'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Warning Messages */}
        {!localState.servicenow_enabled && !localState.jira_enabled && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
            <div>
              <h5 className="text-sm font-semibold text-yellow-900 mb-1">No Integrations Enabled</h5>
              <p className="text-sm text-yellow-800">
                Enable at least one integration to create tickets automatically. Tickets will be created in
                preview mode only when both integrations are disabled.
              </p>
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-200">
          <div className="flex items-center gap-2">
            {saveSuccess && (
              <>
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <span className="text-sm text-green-600 font-medium">Settings saved successfully</span>
              </>
            )}
          </div>
          <button
            onClick={handleSave}
            disabled={!hasChanges || loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            <Save className="w-4 h-4" />
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TicketSettingsPanel;
