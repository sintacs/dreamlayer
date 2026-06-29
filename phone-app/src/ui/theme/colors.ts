export const colors = {
  background:       "#000000",
  surface:          "#0E1416",
  surfaceElevated:  "#141F23",
  textPrimary:      "#FFFFFF",
  textSecondary:    "#8A9BA3",
  accentMemory:     "#2FD4C4",
  accentAttention:  "#FF6B5E",
  accentSuccess:    "#56D364",
  accentError:      "#FF5C5C",
  borderSubtle:     "#1F2A2E",
  statusPaused:     "#6B7A82",
  shimmer:          "#1A2830",
} as const;
export type ColorToken = keyof typeof colors;
