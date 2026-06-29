import { Text } from "react-native";
import { colors } from "../theme/colors";
import { typography } from "../theme/typography";
type Props = { label: string; accent?: string };
export function EyebrowLabel({ label, accent }: Props) {
  return (
    <Text style={[typography.eyebrow, { color: accent ?? colors.accentMemory, marginBottom: 10 }]}>
      {label}
    </Text>
  );
}
