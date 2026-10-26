import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlowValue AI · Process economics",
  description:
    "Interactive techno-economic assessment for chemical and clean technology engineering.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
