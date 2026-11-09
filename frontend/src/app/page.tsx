import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
      <h1 className="text-3xl font-bold">رنتال</h1>
      <p className="text-muted-foreground">
        اجاره ساعتی و روزانه خودرو و دوچرخه
      </p>
      <Button>شروع کنید</Button>
    </main>
  );
}