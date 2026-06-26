import React from "react";
import Link from "next/link";

interface PresentationCardProps {
  title: string;
  description: string;
  href?: string;
  icon?: string;
  badge?: {
    text: string;
    color: string;
  };
  features?: string[];
  onClick?: () => void;
}

export default function PresentationCard({
  title,
  description,
  href,
  icon = "📄",
  badge,
  features,
  onClick,
}: PresentationCardProps) {
  const cardContent = (
    <div className="rounded-[2rem] bg-card/40 backdrop-blur-xl text-card-foreground border border-border/40 shadow-lg hover:shadow-2xl hover:scale-[1.03] transition-all duration-300 p-8 flex flex-col items-center text-center group cursor-pointer">
      {badge && (
        <span className={`inline-flex items-center rounded-full ${badge.color} px-4 py-1.5 text-xs font-semibold mb-4`}>
          {badge.text}
        </span>
      )}
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-2xl font-bold text-gray-800 mb-4">{title}</h3>
      <p className="text-gray-700 text-base mb-6 leading-relaxed">
        {description}
      </p>
      {features && (
        <ul className="list-disc list-inside text-left text-sm text-gray-600 mb-6 space-y-2">
          {features.map((feature, idx) => (
            <li key={idx}>{feature}</li>
          ))}
        </ul>
      )}
    </div>
  );

  if (href) {
    return <Link href={href}>{cardContent}</Link>;
  }

  return <div onClick={onClick}>{cardContent}</div>;
}
