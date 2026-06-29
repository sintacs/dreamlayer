import { TouchableOpacity, Text, ViewStyle } from "react-native";
import { colors } from "../theme/colors";
import { typography } from "../theme/typography";

type Props = { label: string; onPress: () => void; accent?: string; style?: ViewStyle };

export function PrimaryButton({ label, onPress, accent, style }: Props) {
  const bg = accent === "attention" ? colors.accentAttention : colors.accentMemory;
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.8}
      style={[{
        backgroundColor: bg,
        borderRadius: 999,
        paddingVertical: 16,
        paddingHorizontal: 40,
        alignItems: "center",
      }, style]}
    >
      <Text style={[typography.title, { color: colors.background }]}>{label}</Text>
    </TouchableOpacity>
  );
}
