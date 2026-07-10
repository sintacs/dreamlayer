/** The virtual-walk generator for demoing Waypath without GPS (4.7). */
import { simulateWalk } from "../nav/sim";
import { dotFor } from "../nav/waypath";

describe("simulateWalk", () => {
  it("densifies a route into steps that start at the origin and end at the destination", () => {
    const route = [{ lat: 0, lng: 0 }, { lat: 0.02, lng: 0 }]; // ~2.2 km north
    const steps = simulateWalk(route, 500);
    expect(steps.length).toBeGreaterThan(3);
    expect(steps[0]!.pos).toEqual({ lat: 0, lng: 0 });
    expect(steps[steps.length - 1]!.pos).toEqual({ lat: 0.02, lng: 0 });
    // heading points roughly north the whole way
    expect(Math.round(steps[0]!.heading)).toBe(0);
  });

  it("walks the dot from far to arrived", () => {
    const route = [{ lat: 0, lng: 0 }, { lat: 0.02, lng: 0 }];
    const steps = simulateWalk(route, 500);
    const first = dotFor(steps[0]!.pos, steps[0]!.heading, route)!;
    const last = dotFor(steps[steps.length - 1]!.pos, steps[steps.length - 1]!.heading, route)!;
    expect(first.arrived).toBe(false);
    expect(first.distanceM).toBeGreaterThan(1000);
    expect(last.arrived).toBe(true);
  });

  it("handles a single-waypoint route and an empty route", () => {
    expect(simulateWalk([{ lat: 1, lng: 1 }])).toEqual([{ pos: { lat: 1, lng: 1 }, heading: 0 }]);
    expect(simulateWalk([])).toEqual([]);
  });
});
