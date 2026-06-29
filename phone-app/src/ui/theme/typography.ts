import { StyleSheet } from "react-native";
export const typography = StyleSheet.create({
  display:    { fontSize: 36, fontWeight: "700", letterSpacing: -0.5, lineHeight: 42 },
  headline:   { fontSize: 26, fontWeight: "700", letterSpacing: -0.3, lineHeight: 32 },
  title:      { fontSize: 20, fontWeight: "600", lineHeight: 26 },
  body:       { fontSize: 16, fontWeight: "400", lineHeight: 24 },
  caption:    { fontSize: 13, fontWeight: "400", lineHeight: 18, opacity: 0.8 },
  eyebrow:    { fontSize: 11, fontWeight: "600", letterSpacing: 1.5, textTransform: "uppercase" },
  mono:       { fontSize: 13, fontFamily: "monospace", lineHeight: 18 },
});
