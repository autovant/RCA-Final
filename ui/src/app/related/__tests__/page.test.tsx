import { jest } from '@jest/globals';
import axios from 'axios';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import RelatedIncidentsPage from '../page';
import { SAMPLE_RELATED_INCIDENTS } from '@/data/relatedIncidents';

jest.mock('axios');

type AxiosMock = {
  get: jest.MockedFunction<(url: string, config?: unknown) => Promise<unknown>>;
  post: jest.MockedFunction<(url: string, data?: unknown, config?: unknown) => Promise<unknown>>;
};

const mockedAxios = axios as unknown as AxiosMock;

describe('RelatedIncidentsPage', () => {
  beforeEach(() => {
    const { get, post } = mockedAxios;
    resetAxiosMocks();
    get.mockResolvedValue({
      data: { results: SAMPLE_RELATED_INCIDENTS, audit_token: 'audit-123' },
    });
    post.mockResolvedValue({
      data: { results: SAMPLE_RELATED_INCIDENTS, audit_token: 'audit-123' },
    });
  });

  it('renders preview dataset on initial load', () => {
    render(<RelatedIncidentsPage />);

    expect(
      screen.getByText(/Automation flaked after orchestrator patch rollout/i),
    ).toBeInTheDocument();
  });

  it('requires a session identifier before running lookup', async () => {
    render(<RelatedIncidentsPage />);

    const submitButton = screen.getByRole('button', { name: /Run similarity lookup/i });
    fireEvent.click(submitButton);

    expect(
      await screen.findByText(/Enter a session identifier to look up related incidents/i),
    ).toBeInTheDocument();
    expect(mockedAxios.get).not.toHaveBeenCalled();
  });

  it('falls back to preview data when search returns no matches and honors workspace scope overrides', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: { results: [], audit_token: null },
    });

    render(<RelatedIncidentsPage />);

    fireEvent.click(screen.getByRole('button', { name: /Search by description/i }));

  const queryInput = screen.getByPlaceholderText(/Customer login failures/i);
    fireEvent.change(queryInput, { target: { value: 'Edge case outage' } });

  const workspaceInput = screen.getByPlaceholderText(/workspace-123/i);
    fireEvent.change(workspaceInput, { target: { value: 'tenant-123' } });

    const submitButton = screen.getByRole('button', { name: /Run similarity lookup/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledTimes(1);
    });

    const [, payload] = mockedAxios.post.mock.calls[0] ?? [];
    expect(payload).toEqual({
      query: 'Edge case outage',
      scope: 'current_workspace',
      min_relevance: 0.6,
      limit: 10,
      platform: undefined,
      workspace_id: 'tenant-123',
    });

    expect(
      await screen.findByText(/Live search returned no matches/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Automation flaked after orchestrator patch rollout/i),
    ).toBeInTheDocument();
  });
});

function resetAxiosMocks() {
  mockedAxios.get.mockReset();
  mockedAxios.post.mockReset();
}
