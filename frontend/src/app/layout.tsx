import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/vazirmatn";
import "./globals.css";
import { DirectionProvider } from "@/components/ui/direction";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "رنتال",
  description: "اجاره ساعتی و روزانه خودرو و دوچرخه",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <DirectionProvider direction="rtl">
          <AuthProvider>{children}</AuthProvider>
        </DirectionProvider>
      </body>
    </html>
  );
}