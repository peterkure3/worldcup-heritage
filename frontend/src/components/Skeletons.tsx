import { useEffect, useState, useRef } from 'react';

interface StaggerProps {
  children: React.ReactNode;
  index?: number;
  className?: string;
}

export function StaggerIn({ children, index = 0, className }: StaggerProps) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 40 + index * 50);
    return () => clearTimeout(timer);
  }, [index]);

  return (
    <div
      ref={ref}
      className={`${className || ''} stagger-item ${visible ? 'stagger-visible' : ''}`}
      style={{ transitionDelay: `${index * 50}ms` }}
    >
      {children}
    </div>
  );
}

export function SkeletonGroupCard() {
  return (
    <div className="skeleton skeleton-card">
      <div className="skeleton-header" />
      <div className="skeleton-body">
        <div className="skeleton-flex">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton-chip" />
          ))}
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton-row" />
        ))}
      </div>
    </div>
  );
}

export function SkeletonMatchCard() {
  return (
    <div className="skeleton skeleton-card">
      <div className="skeleton-match-teams">
        <div className="skeleton-circle" />
        <div className="skeleton-vs" />
        <div className="skeleton-circle" />
      </div>
      <div className="skeleton-bar" />
      <div className="skeleton-footer">
        <div className="skeleton-tag" />
        <div className="skeleton-tag short" />
      </div>
    </div>
  );
}

export function SkeletonBracket() {
  return (
    <div className="skeleton skeleton-bracket">
      <div className="skeleton-bracket-rounds">
        {[1, 2, 3, 4, 5].map((r) => (
          <div key={r} className="skeleton-round">
            <div className="skeleton-round-label" />
            {[1, 2, 3, 4].map((m) => (
              <div key={m} className="skeleton-match" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonChampionBar() {
  return (
    <div className="skeleton skeleton-champion">
      <div className="skeleton-chart-title" />
      <div className="skeleton-chart-bars">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="skeleton-chart-row">
            <div className="skeleton-chart-label" />
            <div className="skeleton-chart-bar" style={{ width: `${30 + Math.random() * 60}%` }} />
          </div>
        ))}
      </div>
    </div>
  );
}
