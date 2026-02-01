/**
 * BLOCK 8.8: Loading state (ANALYZING).
 */
export default function LoadingState() {
  return (
    <div className="ai-section">
      <div className="ai-card">
        <p className="ai-muted" style={{ margin: 0 }} aria-live="polite">
          Analyzing… Cancel to abort.
        </p>
      </div>
    </div>
  );
}
