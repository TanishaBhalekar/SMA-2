import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { api, detectActiveBackend } from '../api/client';

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(true);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const persistingPromiseRef = useRef(null);

  // Format default session name using current local timestamp
  const getDefaultSessionName = () => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
    return `Session - ${dateStr} ${timeStr}`;
  };

  // Construct a pristine in-memory draft session
  const createDraftWorkspace = (customName = null, customDesc = null) => ({
    id: null,
    name: customName?.trim() || getDefaultSessionName(),
    description: customDesc || 'Interactive Progressive Ingestion Session',
    isDraft: true,
    total_sources: 0,
    total_records: 0,
    total_attributes_indexed: 0,
    master_entities: 0,
    links_discovered: 0,
    created_at: new Date().toISOString(),
    sources: [],
    stats: {
      total_sources: 0,
      total_records: 0,
      total_attributes_indexed: 0,
      master_entities: 0,
      links_discovered: 0,
      multi_hop_links: 0,
    },
  });

  // Fetch all saved workspaces and their aggregated stats
  const refreshWorkspaces = useCallback(async () => {
    try {
      const res = await api.listWorkspaces();
      const list = res.data || [];
      setWorkspaces(list);
      return list;
    } catch (err) {
      console.error('Failed to load workspaces:', err);
      return [];
    }
  }, []);

  // Initialize a new local draft session in React state (no SQLite row created)
  const createNewWorkspace = (customName = null, customDesc = null) => {
    const draft = createDraftWorkspace(customName, customDesc);
    setCurrentWorkspace(draft);
    localStorage.removeItem('active_workspace_id');
    return draft;
  };

  // Lazily persist the draft session to SQLite on first upload or confirmed ingestion
  const ensurePersistedWorkspace = async () => {
    if (currentWorkspace?.id && !currentWorkspace?.isDraft) {
      return currentWorkspace;
    }

    if (persistingPromiseRef.current) {
      return persistingPromiseRef.current;
    }

    persistingPromiseRef.current = (async () => {
      try {
        const name = currentWorkspace?.name?.trim() || getDefaultSessionName();
        const description = currentWorkspace?.description || 'Interactive Progressive Ingestion Session';
        const res = await api.createWorkspace({
          name,
          description,
        });
        const newWs = res.data;
        setCurrentWorkspace(newWs);
        localStorage.setItem('active_workspace_id', newWs.id);
        await refreshWorkspaces();
        return newWs;
      } catch (err) {
        console.error('Failed to persist draft workspace:', err);
        throw err;
      } finally {
        persistingPromiseRef.current = null;
      }
    })();

    return persistingPromiseRef.current;
  };

  // Switch to a past persisted session
  const switchWorkspace = async (workspaceId) => {
    setLoadingWorkspaces(true);
    try {
      const res = await api.getWorkspace(workspaceId);
      const wsData = res.data;
      setCurrentWorkspace(wsData);
      localStorage.setItem('active_workspace_id', workspaceId);
      setHistoryDrawerOpen(false);
      await refreshWorkspaces();
      return wsData;
    } catch (err) {
      console.error('Failed to switch workspace:', err);
      // Fallback to fresh local draft if selected session is missing
      return createNewWorkspace();
    } finally {
      setLoadingWorkspaces(false);
    }
  };

  // Rename a session (updates local draft state or updates DB if persisted)
  const renameWorkspace = async (workspaceId, newName) => {
    if (!newName?.trim()) return;
    const trimmed = newName.trim();

    if (currentWorkspace?.isDraft || !workspaceId || (currentWorkspace?.id === workspaceId && currentWorkspace?.isDraft)) {
      setCurrentWorkspace((prev) => ({ ...prev, name: trimmed }));
      return { ...(currentWorkspace || {}), name: trimmed, isDraft: true };
    }

    try {
      const res = await api.updateWorkspace(workspaceId, { name: trimmed });
      const updated = res.data;
      if (currentWorkspace?.id === workspaceId) {
        setCurrentWorkspace((prev) => ({ ...prev, name: updated.name }));
      }
      await refreshWorkspaces();
      return updated;
    } catch (err) {
      console.error('Failed to rename session:', err);
      throw err;
    }
  };

  // Delete a session with cascade
  const deleteWorkspace = async (workspaceId) => {
    if (!workspaceId) {
      createNewWorkspace();
      return;
    }
    try {
      await api.deleteWorkspace(workspaceId);
      const updatedList = await refreshWorkspaces();

      // If active session was deleted, switch to another or start a clean draft
      if (currentWorkspace?.id === workspaceId) {
        if (updatedList.length > 0) {
          await switchWorkspace(updatedList[0].id);
        } else {
          createNewWorkspace();
        }
      }
    } catch (err) {
      console.error('Failed to delete workspace:', err);
      throw err;
    }
  };

  // Purge all empty orphan sessions (workspaces with 0 sources)
  const purgeEmptySessions = async () => {
    try {
      const res = await api.purgeEmptyWorkspaces();
      const updatedList = await refreshWorkspaces();

      // If active workspace was an empty persisted workspace that got purged
      if (currentWorkspace?.id && !currentWorkspace?.isDraft) {
        const stillExists = updatedList.some((w) => w.id === currentWorkspace.id);
        if (!stillExists) {
          if (updatedList.length > 0) {
            await switchWorkspace(updatedList[0].id);
          } else {
            createNewWorkspace();
          }
        }
      }
      return res.data;
    } catch (err) {
      console.error('Failed to purge empty workspaces:', err);
      throw err;
    }
  };

  // Initial load
  useEffect(() => {
    let mounted = true;

    async function init() {
      setLoadingWorkspaces(true);
      try {
        await detectActiveBackend();
        const list = await refreshWorkspaces();

        const savedId = localStorage.getItem('active_workspace_id');
        if (savedId) {
          const match = list.find((w) => w.id === savedId);
          if (match) {
            if (mounted) setCurrentWorkspace(match);
            return;
          }
        }

        // Clean default landing experience:
        // If no saved active session exists, start with a pristine clean local Draft (no DB write)
        if (mounted) {
          createNewWorkspace();
        }
      } catch (err) {
        console.error('Error during workspace context initialization:', err);
        if (mounted) {
          createNewWorkspace();
        }
      } finally {
        if (mounted) setLoadingWorkspaces(false);
      }
    }

    init();
    return () => { mounted = false; };
  }, [refreshWorkspaces]);

  const value = {
    currentWorkspace,
    workspaces,
    loadingWorkspaces,
    historyDrawerOpen,
    setHistoryDrawerOpen,
    refreshWorkspaces,
    switchWorkspace,
    createNewWorkspace,
    ensurePersistedWorkspace,
    renameWorkspace,
    deleteWorkspace,
    purgeEmptySessions,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
