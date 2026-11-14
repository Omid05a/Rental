import { ANGLE_LABEL, type Angle, type TripPhoto } from "@/lib/bookings";

function Thumb({ photo }: { photo?: TripPhoto }) {
  if (!photo) {
    return (
      <div className="flex aspect-square items-center justify-center rounded-2xl bg-secondary text-xs text-muted-foreground">
        ثبت نشده
      </div>
    );
  }
  return (
    <a
      href={photo.image}
      target="_blank"
      rel="noopener noreferrer"
      className="block aspect-square overflow-hidden rounded-2xl bg-secondary"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={photo.image} alt="" className="size-full object-cover" />
    </a>
  );
}

export function InspectionCompare({
  angles,
  start,
  end,
}: {
  angles: Angle[];
  start: TripPhoto[];
  end: TripPhoto[];
}) {
  if (start.length === 0 && end.length === 0) return null;

  return (
    <section className="flex flex-col gap-3 rounded-3xl bg-card p-5">
      <h3 className="font-semibold">عکس‌های بازرسی</h3>

      <div className="grid grid-cols-[4rem_1fr_1fr] gap-2 text-center text-xs text-muted-foreground">
        <span />
        <span>قبل از سفر</span>
        <span>بعد از سفر</span>
      </div>

      <ul className="flex flex-col gap-2">
        {angles.map((angle) => (
          <li
            key={angle}
            className="grid grid-cols-[4rem_1fr_1fr] items-center gap-2"
          >
            <span className="text-xs text-muted-foreground">
              {ANGLE_LABEL[angle]}
            </span>
            <Thumb photo={start.find((photo) => photo.angle === angle)} />
            <Thumb photo={end.find((photo) => photo.angle === angle)} />
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        برای دیدن عکس در اندازه کامل، روی آن بزنید.
      </p>
    </section>
  );
}