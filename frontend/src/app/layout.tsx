import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlowValue AI",
  description: "AI-driven techno-economic assessment for Chemical & CleanTech Engineering",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
