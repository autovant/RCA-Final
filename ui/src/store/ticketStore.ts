import { create } from 'zustand';
import { Ticket, TicketToggleState, TemplateMetadata, TicketPlatform } from '@/types/tickets';
import ticketApi from '@/lib/api/tickets';
import toast from 'react-hot-toast';

interface TicketStore {
  // State
  tickets: Ticket[];
  currentTicket: Ticket | null;
  toggleState: TicketToggleState | null;
  loading: boolean;
  error: string | null;
  searchQuery: string;
  filterPlatform: 'all' | 'servicenow' | 'jira';
  filterStatus: 'all' | string;
  
  // Template state
  templates: TemplateMetadata[];
  selectedTemplate: TemplateMetadata | null;
  templatesLoading: boolean;

  // Actions
  loadJobTickets: (jobId: string, refresh?: boolean) => Promise<void>;
  loadToggleState: () => Promise<void>;
  updateToggleState: (data: Partial<TicketToggleState>) => Promise<void>;
  setCurrentTicket: (ticket: Ticket | null) => void;
  setSearchQuery: (query: string) => void;
  setFilterPlatform: (platform: 'all' | 'servicenow' | 'jira') => void;
  setFilterStatus: (status: 'all' | string) => void;
  refreshTickets: (jobId: string) => Promise<void>;
  reset: () => void;
  
  // Template actions
  fetchTemplates: (platform?: TicketPlatform) => Promise<void>;
  selectTemplate: (template: TemplateMetadata | null) => void;
  clearTemplate: () => void;
}

const initialState = {
  tickets: [],
  currentTicket: null,
  toggleState: null,
  loading: false,
  error: null,
  searchQuery: '',
  filterPlatform: 'all' as const,
  filterStatus: 'all' as const,
  templates: [],
  selectedTemplate: null,
  templatesLoading: false,
};

export const useTicketStore = create<TicketStore>((set, get) => ({
  ...initialState,

  loadJobTickets: async (jobId: string, refresh = false) => {
    set({ loading: true, error: null });
    try {
      const response = await ticketApi.getJobTickets(jobId, refresh);
      set({ 
        tickets: response.tickets, 
        loading: false 
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to load tickets';
      set({ 
        error: errorMessage, 
        loading: false 
      });
      toast.error(errorMessage);
    }
  },

  loadToggleState: async () => {
    try {
      const state = await ticketApi.getToggleState();
      set({ toggleState: state });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to load toggle state';
      console.error('Failed to load toggle state:', error);
      toast.error(errorMessage);
    }
  },

  updateToggleState: async (data: Partial<TicketToggleState>) => {
    set({ loading: true, error: null });
    try {
      const updatedState = await ticketApi.updateToggleState(data);
      set({ 
        toggleState: updatedState, 
        loading: false 
      });
      toast.success('ITSM settings updated successfully');
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to update toggle state';
      set({ 
        error: errorMessage, 
        loading: false 
      });
      toast.error(errorMessage);
    }
  },

  setCurrentTicket: (ticket) => set({ currentTicket: ticket }),

  setSearchQuery: (query) => set({ searchQuery: query }),

  setFilterPlatform: (platform) => set({ filterPlatform: platform }),

  setFilterStatus: (status) => set({ filterStatus: status }),

  refreshTickets: async (jobId: string) => {
    await get().loadJobTickets(jobId, true);
    toast.success('Ticket status refreshed');
  },

  reset: () => set(initialState),
  
  // Template actions
  fetchTemplates: async (platform?: TicketPlatform) => {
    set({ templatesLoading: true });
    try {
      const response = await ticketApi.getTemplates(platform);
      set({ 
        templates: response.templates,
        templatesLoading: false 
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to load templates';
      console.error('Failed to load templates:', error);
      set({ templatesLoading: false });
      toast.error(errorMessage);
    }
  },

  selectTemplate: (template: TemplateMetadata | null) => {
    set({ selectedTemplate: template });
  },

  clearTemplate: () => {
    set({ selectedTemplate: null });
  },
}));

// Selector hooks for filtered tickets
export const useFilteredTickets = () => {
  const { tickets, searchQuery, filterPlatform, filterStatus } = useTicketStore();
  
  return tickets.filter((ticket) => {
    // Platform filter
    if (filterPlatform !== 'all' && ticket.platform !== filterPlatform) {
      return false;
    }
    
    // Status filter
    if (filterStatus !== 'all' && ticket.status !== filterStatus) {
      return false;
    }
    
    // Search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        ticket.ticket_id.toLowerCase().includes(query) ||
        ticket.status.toLowerCase().includes(query) ||
        ticket.platform.toLowerCase().includes(query)
      );
    }
    
    return true;
  });
};
