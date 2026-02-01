/**
 * BLOCK 8.8: Idle state — before any analysis.
 */
export default function IdleState() {
  return (
    <div className="ai-section">
      <div className="ai-card ai-empty-state">
        <svg className="ai-empty-state__icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <p className="ai-empty-state__text">
          Enter teams and run analysis to see predictions.
        </p>
      </div>
    </div>
  );
}
