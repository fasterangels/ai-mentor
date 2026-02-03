/**
 * Home screen — category card (icon, title, description).
 * Entire card is clickable; no nested CTA button.
 */
export type HomeCardTone = "predictions" | "history" | "statistics" | "settings";

export interface HomeActionCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  tone: HomeCardTone;
  onClick?: () => void;
}

export default function HomeActionCard({
  title,
  description,
  icon,
  tone,
  onClick,
}: HomeActionCardProps) {
  return (
    <button
      type="button"
      className={`ai-home-card ai-home-card--${tone}`}
      onClick={onClick}
    >
      <div className="ai-home-card__header">
        <div className="ai-home-card__icon" aria-hidden>
          {icon}
        </div>
        <h3 className="ai-home-card__title">{title}</h3>
      </div>
      <p className="ai-home-card__desc">{description}</p>
      <span className="ai-home-card__chevron" aria-hidden>
        →
      </span>
    </button>
  );
}
