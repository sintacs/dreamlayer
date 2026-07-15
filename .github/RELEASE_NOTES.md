The first release from the open source repo. DreamLayer went Apache-2.0 (the whole stack), so releases now live here, right next to the code they're built from. The old `dreamlayer-releases` repo is retired, and the version numbering restarts at 0.1.0 with this move. If you have a `v0.6.x` build from the old repo, this release is newer, not older.

## Install (macOS 12+)

Download `DreamLayer.dmg` below, double-click it, drag DreamLayer to Applications. It runs from the menu bar. The app is signed and notarized, so there is no Gatekeeper warning.

## What's in the app

The Mac Brain: the private half of your setup. It indexes the folders and mail you point it at, serves the control panel, and pairs with the phone app and glasses with one code.

New since the last public build:

- A Capabilities tab in the panel. Every optional upgrade the Brain can run (bigger local models, extra memory backends, vision) is listed with what it does and how big a step up it is, with one-click install. The best ones come grouped as packs.
- Juno, the look-at-a-thing lens, with its voice and greetings.
- The plugin store wired end to end: browse, validate, install from the panel, and sideload through the same gate.
- A no-code Lens Builder and a browser simulator, both linked from the panel.
- Faster local search (sqlite-vec index), a unified speech backend (sherpa-onnx), and Apple-Silicon-native model support (MLX).
- Cloud is now opt-in and off by default. The panel says exactly what leaves the machine, and Incognito still forces everything off.
- A pile of hardening from the security audit, including CSRF protection on every panel write.

## Good to know

- This is a pre-hardware build. The Brain, panel, phone pairing, plugins, and simulator are all real and running. The physical glasses seams (camera, mic, BLE) connect when hardware does.
- The full source for everything in this dmg is this repository. Build it yourself with `.github/workflows/build-macos-app.yml` as the recipe.
- Found something broken? Open an issue. Want to build a lens? Start at `examples/hello-lens`.
