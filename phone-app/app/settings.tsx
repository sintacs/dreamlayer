import React from "react";
import { View, Text, Switch, SafeAreaView, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { useHaloStore }   from "../src/state/useHaloStore";
import { useMemoryStore } from "../src/state/useMemoryStore";
import { colors }    from "../src/ui/theme/colors";
import { typography } from "../src/ui/theme/typography";

function Row({ label, sub, right }: { label: string; sub?: string; right: React.ReactNode }) {
  return (
    <View style={s.row}>
      <View style={{ flex: 1 }}>
        <Text style={[typography.body, { color: colors.textPrimary }]}>{label}</Text>
        {sub && <Text style={[typography.caption, { color: colors.textSecondary }]}>{sub}</Text>}
      </View>
      {right}
    </View>
  );
}

export default function Settings() {
  const { paused, togglePause, connected } = useHaloStore();
  const { service } = useMemoryStore();
  const confirmPurge = () =>
    Alert.alert("Erase all memories?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      { text: "Erase", style: "destructive", onPress: () => { service.purgeAll(); } },
    ]);
  return (
    <SafeAreaView style={s.safe}>
      <Text style={[typography.title, s.heading]}>Settings</Text>
      <View style={s.section}>
        <Text style={[typography.eyebrow, { color: colors.accentMemory, marginBottom: 14 }]}>Privacy</Text>
        <Row label="Pause memory capture" sub="Nothing is captured while paused"
          right={<Switch value={paused} onValueChange={togglePause} trackColor={{ true: colors.statusPaused }} />} />
      </View>
      <View style={s.section}>
        <Text style={[typography.eyebrow, { color: colors.accentMemory, marginBottom: 14 }]}>Device</Text>
        <Row label="Halo" sub={connected ? "Connected" : "Not connected"}
          right={<Text style={[typography.caption, { color: connected ? colors.accentSuccess : colors.textSecondary }]}>{connected ? "\u25CF" : "\u25CB"}</Text>} />
      </View>
      <View style={s.section}>
        <Text style={[typography.eyebrow, { color: colors.accentError, marginBottom: 14 }]}>Danger zone</Text>
        <TouchableOpacity onPress={confirmPurge} style={s.danger}>
          <Text style={[typography.body, { color: colors.accentError }]}>Erase all memories</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}
const s = StyleSheet.create({
  safe:    { flex: 1, backgroundColor: colors.background },
  heading: { color: colors.textPrimary, paddingHorizontal: 24, paddingTop: 24, paddingBottom: 8 },
  section: { marginHorizontal: 24, marginTop: 32 },
  row:     { flexDirection: "row", alignItems: "center", paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: colors.borderSubtle },
  danger:  { paddingVertical: 16, alignItems: "center", borderRadius: 12, borderWidth: 1, borderColor: colors.accentError },
});
