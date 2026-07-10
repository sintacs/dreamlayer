/**
 * sim.ts — a virtual walk along a route, for demoing Waypath (4.7) without real
 * GPS. Densifies the polyline into ~stepM-apart positions, each with a heading
 * toward the next point, so the screen can feed them to the store on a timer and
 * you watch the dot lean, close in, and arrive.
 */
import { bearing, haversine, type LatLng } from "./waypath";

export type SimStep = { pos: LatLng; heading: number };

export function simulateWalk(route: LatLng[], stepM = 30): SimStep[] {
  const steps: SimStep[] = [];
  for (let i = 0; i < route.length - 1; i++) {
    const a = route[i];
    const b = route[i + 1];
    if (!a || !b) continue;
    const n = Math.max(1, Math.ceil(haversine(a, b) / stepM));
    const hdg = bearing(a, b);
    for (let k = 0; k < n; k++) {
      const t = k / n;
      steps.push({
        pos: { lat: a.lat + (b.lat - a.lat) * t, lng: a.lng + (b.lng - a.lng) * t },
        heading: hdg,
      });
    }
  }
  const last = route[route.length - 1];
  if (last) {
    const prevHeading = steps.length ? steps[steps.length - 1]!.heading : 0;
    steps.push({ pos: last, heading: prevHeading });
  }
  return steps;
}
