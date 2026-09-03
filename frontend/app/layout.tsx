import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { Nav } from "@/components/Nav";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Structure-to-Safety",
  description:
    "Multimodal computational pharmacology of anabolic-androgenic steroids: exploring whether " +
    "molecular/receptor similarity corresponds to FAERS safety-reporting-profile similarity.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900">
        <Nav />
        <DisclaimerBanner />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
          Structure-to-Safety is a research/portfolio project. It does not provide dosing, cycle,
          or product-safety recommendations. See{" "}
          <a href="/limitations" className="underline">
            Limitations
          </a>
          .
        </footer>
      </body>
    </html>
  );
}
