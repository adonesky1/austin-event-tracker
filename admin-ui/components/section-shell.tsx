import { ReactNode } from "react";

type Props = {
  title: string;
  description: string;
  children: ReactNode;
};

export function SectionShell({ title, description, children }: Props) {
  return (
    <section className="page-section">
      <div className="page-section-header">
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}
