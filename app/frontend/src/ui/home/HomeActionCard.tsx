/**
 * Home screen — action card (title, description, button). PURE UI; onClick placeholder allowed.
 */
export interface HomeActionCardProps {
  title: string;
  description: string;
  buttonLabel: string;
  primary?: boolean;
  onClick?: () => void;
}

export default function HomeActionCard({
  title,
  description,
  buttonLabel,
  primary = false,
  onClick,
}: HomeActionCardProps) {
  return (
    <div className="ai-home-card">
      <h3 className="ai-home-card__title">{title}</h3>
      <p className="ai-home-card__desc">{description}</p>
      <button
        type="button"
        className={primary ? "ai-btn ai-btn--primary" : "ai-btn ai-btn--ghost"}
        onClick={onClick ?? (() => {})}
        aria-label={buttonLabel}
      >
        {buttonLabel}
      </button>
    </div>
  );
}
