import { Link } from "react-router-dom";
import type { ReactNode } from "react";

interface NavCardProps {
  title: string;
  description: string;
  to: string;
  icon: ReactNode;
}

export function NavCard({ title, description, to, icon }: NavCardProps) {
  return (
    <Link
      to={to}
      className="block p-6 bg-white border border-gray-200 rounded-lg hover:border-gray-300 hover:shadow-sm transition-shadow"
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-gray-600">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <p className="mt-1 text-sm text-gray-500">{description}</p>
          <span className="mt-2 inline-block text-sm font-medium text-blue-600">
            Μετάβαση →
          </span>
        </div>
      </div>
    </Link>
  );
}
