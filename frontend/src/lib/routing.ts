export type LatLngTuple = [number, number];
export type RoutePoint = { lat: number; lng: number };

export type RouteResult = {
  path: LatLngTuple[];
  distanceM: number;
  durationS: number;
  mode: "walking" | "driving";
};

// Public OSRM demo services: best effort, no guarantees, at most about one
// request per second.
const SERVICES: { mode: RouteResult["mode"]; url: string }[] = [
  {
    mode: "walking",
    url: "https://routing.openstreetmap.de/routed-foot/route/v1/driving",
  },
  {
    mode: "driving",
    url: "https://router.project-osrm.org/route/v1/driving",
  },
];

// The walking profile is only used for short trips. Pedestrians cannot use
// motorways, so on long trips it returns huge detours.
const WALKING_MAX_M = 3000;
const TIMEOUT_MS = 7000;

type OsrmResponse = {
  code: string;
  routes?: {
    distance: number;
    duration: number;
    geometry: { coordinates: [number, number][] };
  }[];
};

async function requestRoute(
  baseUrl: string,
  from: RoutePoint,
  to: RoutePoint,
): Promise<OsrmResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const coords = `${from.lng},${from.lat};${to.lng},${to.lat}`;
    const response = await fetch(
      `${baseUrl}/${coords}?overview=full&geometries=geojson`,
      { signal: controller.signal },
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return (await response.json()) as OsrmResponse;
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchRoute(
  from: RoutePoint,
  to: RoutePoint,
): Promise<RouteResult> {
  const straightM = straightDistanceM(from, to);
  const services =
    straightM <= WALKING_MAX_M
      ? SERVICES
      : SERVICES.filter((service) => service.mode === "driving");

  for (const service of services) {
    try {
      const data = await requestRoute(service.url, from, to);
      const route = data.code === "Ok" ? data.routes?.[0] : undefined;
      if (route) {
        // A walking route far longer than the straight line usually means the
        // foot profile had to avoid a motorway; use the driving route instead.
        if (service.mode === "walking" && route.distance > straightM * 2.5 + 500) {
          continue;
        }
        return {
          // OSRM returns [lng, lat]; Leaflet expects [lat, lng].
          path: route.geometry.coordinates.map(
            ([lng, lat]) => [lat, lng] as LatLngTuple,
          ),
          distanceM: route.distance,
          durationS: route.duration,
          mode: service.mode,
        };
      }
    } catch {
      // Try the next service.
    }
  }
  throw new Error("Route service unavailable");
}

/** Straight-line distance in meters (haversine). */
export function straightDistanceM(a: RoutePoint, b: RoutePoint): number {
  const toRad = (value: number) => (value * Math.PI) / 180;
  const earthRadius = 6_371_000;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * earthRadius * Math.asin(Math.sqrt(h));
}