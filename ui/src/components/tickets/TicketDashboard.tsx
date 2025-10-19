'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  RefreshCw,
  Search,
  Filter,
  AlertCircle,
  ExternalLink,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { useTicketStore, useFilteredTickets } from '@/store/ticketStore';
import { Ticket } from '@/types/tickets';
import {
  getStatusConfig,
  getPlatformConfig,
  formatDate,
  formatRelativeTime,
} from '@/lib/utils/ticketUtils';
import { Alert, Button, Card, Input, Spinner } from '@/components/ui';

interface TicketDashboardProps {
  jobId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const TicketDashboard: React.FC<TicketDashboardProps> = ({
  jobId,
  autoRefresh = false,
  refreshInterval = 60000,
}) => {
  const {
    loading,
    error,
    searchQuery,
    filterPlatform,
    filterStatus,
    loadJobTickets,
    refreshTickets,
    setSearchQuery,
    setFilterPlatform,
    setFilterStatus,
    setCurrentTicket,
  } = useTicketStore();

  const filteredTickets = useFilteredTickets();
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadJobTickets(jobId);
  }, [jobId, loadJobTickets]);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await refreshTickets(jobId);
    setIsRefreshing(false);
  }, [jobId, refreshTickets]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      handleRefresh();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, handleRefresh]);

  const handleTicketClick = (ticket: Ticket) => {
    setCurrentTicket(ticket);
  };

  const getStatusStats = () => {
    const stats = {
      total: filteredTickets.length,
      new: 0,
      inProgress: 0,
      resolved: 0,
      failed: 0,
    };

    filteredTickets.forEach((ticket) => {
      if (ticket.status === 'New') stats.new++;
      else if (ticket.status === 'In Progress') stats.inProgress++;
      else if (ticket.status === 'Resolved' || ticket.status === 'Closed') stats.resolved++;
      else if (ticket.dry_run && ticket.metadata?.error) stats.failed++;
    });

    return stats;
  };

  const stats = getStatusStats();

  return (
    <div className="w-full space-y-6">
      <Card className="p-6 lg:p-8">
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-dark-text-primary">Incident Tickets</h2>
              <p className="text-sm text-dark-text-secondary">
                Coordinate ServiceNow and Jira activity directly from this run.
              </p>
            </div>
            <Button
              onClick={handleRefresh}
              loading={isRefreshing}
              disabled={loading && !isRefreshing}
              icon={<RefreshCw className="w-4 h-4" />}
            >
              Refresh Status
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-dark-border/60 bg-dark-bg-tertiary/60 p-4 shadow-fluent">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-dark-text-tertiary">Total Tickets</p>
                  <p className="mt-2 text-3xl font-semibold text-dark-text-primary">{stats.total}</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-fluent-blue-500/10 text-2xl">
                  📋
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-dark-border/60 bg-gradient-to-br from-fluent-blue-500/10 via-dark-bg-tertiary/60 to-dark-bg-tertiary/80 p-4 shadow-fluent">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-dark-text-tertiary">New</p>
                  <p className="mt-2 text-3xl font-semibold text-dark-text-primary">{stats.new}</p>
                </div>
                <Clock className="h-10 w-10 text-fluent-blue-200" />
              </div>
            </div>

            <div className="rounded-xl border border-dark-border/60 bg-gradient-to-br from-fluent-warning/10 via-dark-bg-tertiary/60 to-dark-bg-tertiary/80 p-4 shadow-fluent">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-dark-text-tertiary">In Progress</p>
                  <p className="mt-2 text-3xl font-semibold text-dark-text-primary">{stats.inProgress}</p>
                </div>
                <AlertCircle className="h-10 w-10 text-yellow-300" />
              </div>
            </div>

            <div className="rounded-xl border border-dark-border/60 bg-gradient-to-br from-fluent-success/10 via-dark-bg-tertiary/60 to-dark-bg-tertiary/80 p-4 shadow-fluent">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-dark-text-tertiary">Resolved</p>
                  <p className="mt-2 text-3xl font-semibold text-dark-text-primary">{stats.resolved}</p>
                </div>
                <CheckCircle2 className="h-10 w-10 text-green-300" />
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
          <Input
            placeholder="Search by ticket ID, status, or platform..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search className="h-4 w-4" />}
            className="flex-1"
          />

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
            <div className="flex items-center gap-2 text-dark-text-tertiary">
              <Filter className="h-4 w-4" />
              <select
                value={filterPlatform}
                onChange={(e) =>
                  setFilterPlatform(e.target.value as 'all' | 'servicenow' | 'jira')
                }
                className="input appearance-none pr-10"
                aria-label="Filter by platform"
              >
                <option value="all">All Platforms</option>
                <option value="servicenow">ServiceNow</option>
                <option value="jira">Jira</option>
              </select>
            </div>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="input appearance-none pr-10"
              aria-label="Filter by status"
            >
              <option value="all">All Statuses</option>
              <option value="New">New</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
              <option value="Closed">Closed</option>
              <option value="dry-run">Preview</option>
            </select>
          </div>
        </div>
      </Card>

      {error && (
        <Alert variant="error" title="Error loading tickets">
          {error}
        </Alert>
      )}

      {loading && !isRefreshing ? (
        <Card className="p-12">
          <div className="flex flex-col items-center gap-4 text-dark-text-secondary">
            <Spinner />
            <p>Loading tickets…</p>
          </div>
        </Card>
      ) : filteredTickets.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-dark-border/60 bg-dark-bg-tertiary/80 text-3xl">
            📋
          </div>
          <h3 className="mt-6 text-lg font-semibold text-dark-text-primary">No Tickets Found</h3>
          <p className="mt-2 text-sm text-dark-text-secondary">
            {searchQuery || filterPlatform !== 'all' || filterStatus !== 'all'
              ? 'Adjust filters or clear your search to broaden the results.'
              : 'Create a ticket from the command center to populate this view.'}
          </p>
        </Card>
      ) : (
        <Card className="p-0">
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Platform</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTickets.map((ticket) => {
                  const statusConfig = getStatusConfig(ticket.status);
                  const platformConfig = getPlatformConfig(ticket.platform);

                  return (
                    <tr
                      key={ticket.id}
                      onClick={() => handleTicketClick(ticket)}
                      className="cursor-pointer"
                    >
                      <td className="font-mono text-sm text-dark-text-primary">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{ticket.ticket_id}</span>
                          {ticket.dry_run && (
                            <span className="badge bg-fluent-info/10 text-fluent-info border border-fluent-info/30">
                              Preview
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <span
                          className={`badge ${platformConfig.bgColor} ${platformConfig.color}`}
                        >
                          <span>{platformConfig.icon}</span>
                          {platformConfig.label}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${statusConfig.bgColor} ${statusConfig.color}`}
                        >
                          <span>{statusConfig.icon}</span>
                          {statusConfig.label}
                        </span>
                      </td>
                      <td className="text-dark-text-secondary">
                        <div className="flex flex-col">
                          <span>{formatRelativeTime(ticket.created_at)}</span>
                          <span className="text-xs text-dark-text-tertiary">
                            {formatDate(ticket.created_at)}
                          </span>
                        </div>
                      </td>
                      <td className="text-dark-text-secondary">
                        {ticket.updated_at ? formatRelativeTime(ticket.updated_at) : '—'}
                      </td>
                      <td>
                        {ticket.url && !ticket.dry_run && (
                          <a
                            href={ticket.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-fluent-blue-200 hover:text-white"
                          >
                            View
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

export default TicketDashboard;
