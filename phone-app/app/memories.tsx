import React from "react";
import { View, Text, FlatList, SafeAreaView, StyleSheet } from "react-native";
import { useMemoryStore } from "../src/state/useMemoryStore";
import { colors }    from "../src/ui/theme/colors";
import { typography } from "../src/ui/theme/typography";

export default function Memories() {
  const { memories, refresh } = useMemoryStore();
  React.useEffect(() => { refresh(); }, []);
  return (
    <SafeAreaView style={s.safe}>
      <Text style={[typography.title, s.heading]}>Memories</Text>
      <FlatList
        data={memories}
        keyExtractor={m => m.id}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        ListEmptyComponent={
          <Text style={[typography.body, { color: colors.textSecondary, textAlign: "center", marginTop: 60 }]}>
            No memories yet.{"\n"}Start wearing your Halo.
          </Text>
        }
        renderItem={({ item }) => (
          <View style={s.card}>
            <Text style={[typography.eyebrow, { color: colors.accentMemory }]}>{item.kind}</Text>
            <Text style={[typography.body,    { color: colors.textPrimary }]}>{item.summary}</Text>
            <Text style={[typography.caption, { color: colors.textSecondary }]}>{item.createdAt}</Text>
          </View>
        )}
      />
    </SafeAreaView>
  );
}
const s = StyleSheet.create({
  safe:    { flex: 1, backgroundColor: colors.background },
  heading: { color: colors.textPrimary, paddingHorizontal: 24, paddingTop: 24, paddingBottom: 8 },
  card:    { backgroundColor: colors.surface, borderRadius: 16, padding: 18, borderWidth: 1, borderColor: colors.borderSubtle, gap: 6 },
});
