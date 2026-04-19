import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DeepTutor - Authentication",
  description: "Sign in to your AI learning workspace",
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
