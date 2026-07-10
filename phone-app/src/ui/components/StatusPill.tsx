import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors } from "../theme/colors";
import { typography } from "../theme/typography";
import { useConnectionStore } from "../../state/useConnectionStore";

/** A small live/paused indicator for the Now header. */
export function StatusPill({ paused }: { paused: boolean }) {
  const tint = paused ? colors.statusPaused : colors.accentSuccess;
  return (
    <View style={[s.pill, { borderColor: tint }]}>
      <View style={[s.dot, { backgroundColor: tint }]} />
      <Text style={[typography.caption, { color: tint }]}>{paused ? "Paused" : "Live"}</Text>
    </View>
  );
}

/** The Brain's three honest reachability truths — home / away via relay /
 * unreachable — rendered from the single connection state machine, never a
 * per-call guess. Renders nothing while no Brain is paired. */
export function BrainPill() {
  const state = useConnectionStore((s) => s.state);
  const labelFn = useConnectionStore((s) => s.label);
  if (state === "unpaired") return null;
  const tint =
    state === "lan" ? colors.accentSuccess : colors.statusPaused;
  return (
    <View style={[s.pill, { borderColor: tint }]}>
      <View style={[s.dot, { backgroundColor: tint }]} />
      <Text style={[typography.caption, { color: tint }]}>{labelFn()}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  pill: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 999,
    paddingVertical: 6,
    paddingHorizontal: 12,
    gap: 7,
  },
  dot: { width: 7, height: 7, borderRadius: 4 },
});
