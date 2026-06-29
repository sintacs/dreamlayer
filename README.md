# Memoscape

**A private memory layer for the real world.**

Memoscape is a premium experience layer for **Brilliant Labs Halo** smart glasses.
It is a host-driven Halo application stack that *feels* like a branded OS: it owns
onboarding, capture, memory, recall, HUD rendering, and privacy.

> Status: **Pre-hardware build.** Everything here runs against the Halo emulator
> and deterministic mocks. The day Halo arrives we pair it, upload the Lua runtime,
> connect the host bridge, and run the first on-device memory recall demo.

## Repo layout
- `docs/` — product spec, architecture, HUD design system, privacy, demos, device-day plan
- `halo-lua/` — Lua 5.3 application that runs on the Halo VM (`main.lua` autoruns)
- `host-python/` — host app + emulator harness + memory engine + tests
- `phone-app/` — lightweight Expo/React Native scaffold (future host UI)
- `scripts/` — runnable emulator + demo + export + test runners
- `assets/` — exported HUD samples and palettes

## Quick start
```bash
cd host-python
pip install -e .
python ../scripts/run_emulator.py
python ../scripts/run_demo_object_recall.py
python ../scripts/run_tests.py
```

## Critical path status
See `docs/IMPLEMENTATION_PLAN.md` for what is complete vs blocked on hardware.
