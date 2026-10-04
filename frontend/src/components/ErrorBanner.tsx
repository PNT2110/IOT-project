import { useEffect, useRef } from "react";

export type ErrorBannerProps = {
  message: string | null;
  onDismiss: () => void;
  autoDismissMs?: number;
  className?: string;
};

/**
 * Accessible ErrorBanner component with 8-second auto-dismiss timer
 * and manual close button (×) with aria-label="Đóng thông báo".
 * Preserves role="alert" and aria-live="assertive".
 * Uses a ref for onDismiss to prevent timer starvation from parent re-renders.
 */
export function ErrorBanner({
  message,
  onDismiss,
  autoDismissMs = 8000,
  className = "",
}: ErrorBannerProps) {
  const onDismissRef = useRef(onDismiss);
  onDismissRef.current = onDismiss;

  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(() => {
      onDismissRef.current();
    }, autoDismissMs);
    return () => {
      window.clearTimeout(timer);
    };
  }, [message, autoDismissMs]);

  if (!message) return null;

  return (
    <div
      className={`error-banner ${className}`.trim()}
      role="alert"
      aria-live="assertive"
    >
      <span className="error-banner-text">{message}</span>
      <button
        type="button"
        className="error-banner-dismiss"
        aria-label="Đóng thông báo"
        onClick={() => onDismissRef.current()}
      >
        ×
      </button>
    </div>
  );
}
