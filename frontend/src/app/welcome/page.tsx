"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";

const SLIDES = [
  {
    image: "/images/welcome-car.svg",
    title: "ماشین، فقط برای چند ساعت",
    text: "ماشین‌های اطراف خودت را ببین، ساعتی یا روزانه اجاره کن و بدون کاغذبازی تحویل بگیر.",
  },
  {
    image: "/images/welcome-bike.svg",
    title: "دوچرخه برای مسیرهای کوتاه",
    text: "برای رفت‌وآمد کوتاه در شهر، دوچرخه‌ای نزدیک پیدا کن و با اسکن QR قفلش را باز کن.",
  },
];

const WELCOME_SEEN_KEY = "rental.welcome_seen";

export default function WelcomePage() {
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const isLast = index === SLIDES.length - 1;

  function finish() {
    try {
      window.localStorage.setItem(WELCOME_SEEN_KEY, "1");
    } catch {
      // Ignore storage errors; the welcome screen will simply show again.
    }
    router.replace("/login");
  }

  return (
    <div className="relative mx-auto min-h-dvh w-full max-w-md overflow-hidden bg-background">
      {SLIDES.map((slide, i) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={slide.image}
          src={slide.image}
          alt=""
          className={`absolute inset-0 h-full w-full object-cover transition-all duration-700 ease-out ${
            i === index ? "scale-100 opacity-100" : "scale-105 opacity-0"
          }`}
        />
      ))}

      <button
        type="button"
        onClick={finish}
        className="press animate-fade-in absolute end-6 top-6 rounded-full bg-black/40 px-4 py-2 text-sm text-white hover:bg-black/60"
      >
        رد کردن
      </button>

      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-6 px-6 pb-10 text-white">
        {/* Re-keyed per slide so the text animates in on every change */}
        <div key={index} className="animate-fade-up">
          <h1 className="text-3xl font-bold leading-snug">
            {SLIDES[index].title}
          </h1>
          <p className="mt-3 text-base leading-relaxed text-white/75">
            {SLIDES[index].text}
          </p>
        </div>

        <div className="flex gap-2" aria-hidden="true">
          {SLIDES.map((slide, i) => (
            <span
              key={slide.image}
              className={`h-1.5 rounded-full transition-all duration-300 ease-out ${
                i === index ? "w-8 bg-primary" : "w-1.5 bg-white/40"
              }`}
            />
          ))}
        </div>

        <Button
          className="animate-fade-up h-14 w-full rounded-full text-base font-bold"
          style={{ animationDelay: "200ms" }}
          onClick={() => (isLast ? finish() : setIndex(index + 1))}
        >
          {isLast ? "شروع کنید" : "بعدی"}
        </Button>
      </div>
    </div>
  );
}