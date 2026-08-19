import { User } from "../types";
import { CentralControl } from "../components/dashboard/CentralControl";

interface Module1PageProps {
  token: string;
  user: User;
}

/** Module 1 — Central Control: default landing screen for all roles. */
export function Module1Page({ token, user }: Module1PageProps) {
  return <CentralControl token={token} user={user} />;
}
