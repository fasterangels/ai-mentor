export interface NotesPanelProps {
  notes: string[];
  warnings: string[];
}

export default function NotesPanel({ notes, warnings }: NotesPanelProps) {
  const hasNotes = notes.length > 0;
  const hasWarnings = warnings.length > 0;
  if (!hasNotes && !hasWarnings) return null;

  return (
    <div className="ai-section">
      <div className="ai-card">
        <div className="ai-cardHeader">
          <div className="ai-cardTitle">Notes &amp; Warnings</div>
        </div>
        {hasWarnings && (
          <div style={{ marginBottom: hasNotes ? 12 : 0 }}>
            <p style={{ fontWeight: 600, margin: "0 0 4px 0", fontSize: 13 }}>Warnings</p>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {warnings.map((w, i) => (
                <li key={i} className="ai-chip--warn" style={{ listStyle: "disc" }}>{w}</li>
              ))}
            </ul>
          </div>
        )}
        {hasNotes && (
          <div>
            <p style={{ fontWeight: 600, margin: "0 0 4px 0", fontSize: 13 }}>Notes</p>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
