import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const grotesk = Space_Grotesk({ variable: "--font-grotesk", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const jbmono = JetBrains_Mono({ variable: "--font-jbmono", subsets: ["latin"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: { default: "7didan · Business catalogue assistant", template: "%s · 7didan" },
  description:
    "Ask about business services in Darija, French or English, get answers that show their source, and send a structured enquiry in three questions. Academic prototype.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { themeColor: "#141110", width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${grotesk.variable} ${jbmono.variable} h-full`}>
      <body className="grain flex min-h-full flex-col">{children}</body>
    </html>
  );
}
