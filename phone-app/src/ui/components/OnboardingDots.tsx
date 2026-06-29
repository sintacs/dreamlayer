import { View } from "react-native";
import { colors } from "../theme/colors";

export function OnboardingDots({ total, current }: { total: number; current: number }) {
  return (
    <View style={{ flexDirection: "row", gap: 8, justifyContent: "center" }}>
      {Array.from({ length: total }).map((_, i) => (
        <View
          key={i}
          style={{
            width:  i === current ? 20 : 6,
            height: 6,
            borderRadius: 3,
            backgroundColor: i === current ? colors.accentMemory : colors.borderSubtle,
          }}
        />
      ))}
    </View>
  );
}
