import React from "react";
import { View, Text, SafeAreaView, TouchableOpacity, StyleSheet } from "react-native";
import { useHaloStore }  from "../src/state/useHaloStore";
import { HaloMirror }   from "../src/ui/components/HaloMirror";
import { StatusPill }   from "../src/ui/components/StatusPill";
import { colors }       from "../src/ui/theme/colors";
import { typography }   from "../src/ui/theme/typography";

export default function Now() {
  const { paused, connected, togglePause, connect, service } = useHaloStore();
  return (
    <SafeAreaView style={s.safe}>
      <View style={s.header}>
        <Text style={[typography.title, { color: colors.textPrimary }]}>Now</Text>
        <StatusPill paused={paused} />
      </View>
      <View style={s.mirror}>
        <HaloMirror card={service.lastCard} />
        {!connected && (
          <Text style={[typography.caption, { color: colors.textSecondary, marginTop: 16, textAlign: "center" }]}>
            Halo not connected.{" "}
            <Text style={{ color: colors.accentMemory }} onPress={() => connect()}>Pair</Text>
          </Text>
        )}
      </View>
      <View style={s.actions}>
        <TouchableOpacity onPress={togglePause} style={[s.pill, { borderColor: paused ? colors.statusPaused : colors.borderSubtle }]}>
          <Text style={[typography.body, { color: paused ? colors.statusPaused : colors.textSecondary }]}>
            {paused ? "Resume memory" : "Pause capture"}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}
const s = StyleSheet.create({
  safe:    { flex: 1, backgroundColor: colors.background },
  header:  { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 24, paddingTop: 24, paddingBottom: 16 },
  mirror:  { flex: 1, alignItems: "center", justifyContent: "center" },
  actions: { padding: 24, gap: 12 },
  pill:    { borderRadius: 999, borderWidth: 1, paddingVertical: 14, paddingHorizontal: 28, alignItems: "center" },
});
