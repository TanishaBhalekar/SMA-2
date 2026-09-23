import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, detectActiveBackend } from '../api/client';

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(true);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);

  // Format default session name using current local timestamp
  const getDefaultSessionName = () => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
    return `Session - ${dateStr} ${timeStr}`;
  };

  // Fetch all workspaces and their aggregated stats
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

  // Create a brand new clean session
  const createNewWorkspace = async (customName = null, customDesc = null) => {
    setLoadingWorkspaces(true);
    try {
      const name = customName?.trim() || getDefaultSessionName();
      const res = await api.createWorkspace({
        name,
        description: customDesc || 'Interactive Progressive Ingestion Session'
      });
      const newWs = res.data;

      // Update active workspace
      setCurrentWorkspace(newWs);
      localStorage.setItem('active_workspace_id', newWs.id);

      // Refresh list
      await refreshWorkspaces();
      return newWs;
    } catch (err) {
      console.error('Failed to create new session:', err);
      throw err;
    } finally {
      setLoadingWorkspaces(false);
    }
  };

  // Switch to a past session
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
      // Fallback to fresh session if selected session is missing
      return await createNewWorkspace();
    } finally {
      setLoadingWorkspaces(false);
    }
  };

  // Rename a session
  const renameWorkspace = async (workspaceId, newName) => {
    if (!newName?.trim()) return;
    try {
      const res = await api.updateWorkspace(workspaceId, { name: newName.trim() });
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
    try {
      await api.deleteWorkspace(workspaceId);
      const updatedList = await refreshWorkspaces();

      // If active session was deleted, switch to another or create a clean one
      if (currentWorkspace?.id === workspaceId) {
        if (updatedList.length > 0) {
          await switchWorkspace(updatedList[0].id);
        } else {
          await createNewWorkspace();
        }
      }
    } catch (err) {
      console.error('Failed to delete workspace:', err);
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
        // If no saved active session exists, start with a pristine clean session canvas
        if (mounted) {
          await createNewWorkspace();
        }
      } catch (err) {
        console.error('Error during workspace context initialization:', err);
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
    renameWorkspace,
    deleteWorkspace,
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
