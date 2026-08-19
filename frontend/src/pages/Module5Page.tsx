import { ComparisonView } from "../components/comparison/ComparisonView";

interface Module5PageProps {
  token: string;
  role: string;
}

/** Module 5 — Changes & Version Intelligence */
export function Module5Page({ token, role }: Module5PageProps) {
  return <ComparisonView token={token} role={role} />;
}
