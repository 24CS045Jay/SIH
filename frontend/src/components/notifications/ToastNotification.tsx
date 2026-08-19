import { useEffect, useState, useCallback } from "react";
import { AlertItem } from "../../types";
import { API, authHeaders } from "../../api/client";

interface Toast {
  id: string;
  title: string;
  priority: string;
}

interface ToastNotificationProps {
  token: string;
}

/**
 * Real-time alert notifications via Server-Sent Events (SSE).
 * Displays toast in top-right for new Critical/High alerts.
 * Does NOT auto-approve anything — it only surfaces items for human review.
 */
export function ToastNotification({ token }: ToastNotificationProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((alert: AlertItem) => {
    if (!["critical", "high"].includes(alert.priority)) return;
    setToasts((prev) => {
      if (prev.some((t) => t.id === alert.id)) return prev;
      return [...prev, { id: alert.id, title: alert.title, priority: alert.priority }].slice(-4);
    });
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== alert.id));
    }, 8000);
  }, []);

  useEffect(() => {
    // SSE connection to the alerts event stream
    const url = `${API}/events/alerts`;
    let es: EventSource | null = null;

    try {
      // EventSource doesn't support custom headers — pass token as query param
      es = new EventSource(`${url}?token=${encodeURIComponent(token)}`);
      es.onmessage = (event) => {
        try {
          const alert: AlertItem = JSON.parse(event.data);
          addToast(alert);
        } catch {
          // ignore malformed events
        }
      };
      es.onerror = () => {
        // SSE connection error — silently reconnect (browser handles automatically)
      };
    } catch {
      // SSE not available in this environment — graceful no-op
    }

    return () => {
      es?.close();
    };
  }, [token, addToast]);

  function dismiss(id: string) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-live="polite" role="status">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.priority}`}>
          <button onClick={() => dismiss(toast.id)} aria-label="Dismiss notification">×</button>
          <strong>New {toast.priority.toUpperCase()} alert</strong>
          {toast.title}
        </div>
      ))}
    </div>
  );
}
