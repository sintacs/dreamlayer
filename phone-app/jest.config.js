/**
 * Store/service unit tests run under plain ts-jest — no Expo runtime, no
 * React renderer. Native-module imports are mapped to tiny in-memory mocks
 * (src/testing/mocks/) so the pure logic — pairing codec, connection state
 * machine, config outbox, haptic vocabulary — is exercised exactly as it
 * ships. UI component tests would add jest-expo; the logic layer must not
 * wait for that.
 */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/src"],
  testMatch: ["**/__tests__/**/*.test.ts"],
  moduleNameMapper: {
    "^@react-native-async-storage/async-storage$":
      "<rootDir>/src/testing/mocks/async-storage.ts",
  },
  transform: {
    "^.+\\.tsx?$": ["ts-jest", { tsconfig: { jsx: "react", esModuleInterop: true } }],
  },
};
