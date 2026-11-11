import type { ComponentProps, ReactNode } from "react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type IconInputProps = ComponentProps<typeof Input> & { icon: ReactNode };

export function IconInput({ icon, className, ...props }: IconInputProps) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute inset-y-0 start-4 flex items-center text-muted-foreground">
        {icon}
      </span>
      <Input
        className={cn(
          "h-14 rounded-full border-0 bg-card ps-12 pe-5 text-base",
          className,
        )}
        {...props}
      />
    </div>
  );
}