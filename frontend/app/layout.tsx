import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bharat Intelligence Agent",
  description: "Multi-source business analytics for Indian SMBs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
