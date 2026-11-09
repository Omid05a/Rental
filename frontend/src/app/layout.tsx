import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/vazirmatn";
import "./globals.css";
import { DirectionProvider } from "@/components/ui/direction";

export const metadata: Metadata = {
  title: "Rental",
  description: "Peer-to-peer rental of cars and bicycles",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <DirectionProvider direction="rtl">{children}</DirectionProvider>
      </body>
    </html>
  );
}