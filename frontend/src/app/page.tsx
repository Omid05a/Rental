"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  const { user, ready } = useAuth();

  useEffect(() => {
    if (!ready) return;
    if (user) {
      router.replace("/profile");
      return;
    }
    let seen = false;
    try {
      seen = window.localStorage.getItem("rental.welcome_seen") === "1";
    } catch {
      // Treat unreadable storage as "not seen".
    }
    router.replace(seen ? "/login" : "/welcome");
  }, [ready, user, router]);

  return <div className="min-h-dvh bg-foreground" />;
}