/**
 * Date and session formatting utilities for consistent local timezone rendering.
 */

/**
 * Format session ISO string to user's local browser date & time.
 * Parses the ISO string consistently with UTC 'Z' indicator.
 */
export const formatSessionDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
};

/**
 * Generate fallback default session name using browser's local time.
 */
export const getDefaultSessionName = () => {
  const localNow = new Date();
  return `Session – ${localNow.toLocaleDateString()} ${localNow.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
};

/**
 * Format session display title. If the title is an auto-generated backend UTC timestamp pattern,
 * format it using the session creation date into the user's local timezone so both the session
 * card title and its subtitle timestamp match the user's local timezone.
 */
export const formatSessionTitle = (ws) => {
  if (!ws) return '';
  const name = typeof ws === 'string' ? ws : (ws.name || '');

  // Backend generated pattern: Session – YYYY-MM-DD HH:MM or Session - YYYY-MM-DD HH:MM
  const defaultUtcPattern = /^Session\s*[–-]\s*\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}(:\d{2})?)?$/;
  if (defaultUtcPattern.test(name.trim())) {
    const dateStr = typeof ws === 'object' ? ws.created_at : null;
    if (dateStr) {
      const d = new Date(dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`);
      return `Session – ${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
  }

  if (!name && typeof ws === 'object' && ws.created_at) {
    const d = new Date(ws.created_at.endsWith('Z') ? ws.created_at : `${ws.created_at}Z`);
    return `Session – ${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  return name;
};
