import { Bike, Car } from "lucide-react";
import Link from "next/link";

import { formatDistance, formatToman } from "@/lib/format";
import { KIND_LABEL, type PublicVehicle } from "@/lib/vehicles";
import { cn } from "@/lib/utils";

export function VehicleCard({
  vehicle,
  highlighted = false,
}: {
  vehicle: PublicVehicle;
  highlighted?: boolean;
}) {
  const Icon = vehicle.kind === "bike" ? Bike : Car;

  return (
    <Link
      href={`/vehicles/${vehicle.id}`}
      className={cn(
        "flex items-center gap-4 rounded-3xl bg-card p-3",
        highlighted && "ring-2 ring-primary",
      )}
    >
      <div className="flex size-24 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-secondary text-muted-foreground">
        {vehicle.cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={vehicle.cover} alt="" className="size-full object-cover" />
        ) : (
          <Icon className="size-9" />
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h3 className="truncate font-semibold">{vehicle.title}</h3>
        <p className="truncate text-xs text-muted-foreground">
          {KIND_LABEL[vehicle.kind]} · {vehicle.brand} {vehicle.model_name}
        </p>
        <p className="text-sm font-bold text-primary">
          {formatToman(vehicle.price_per_hour)}
          <span className="font-normal text-muted-foreground"> / ساعت</span>
        </p>
        <p className="truncate text-xs text-muted-foreground">
          {vehicle.distance_m !== null
            ? `${formatDistance(vehicle.distance_m)} · `
            : ""}
          {formatToman(vehicle.price_per_day)} / روز
        </p>
      </div>
    </Link>
  );
}