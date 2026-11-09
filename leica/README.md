# Leica port 8.x on gauguin

Package `com.kobbin.leica.wmrebuild` (versionName 8.0.0, targetSdk 36, a HyperOS-based
Leica camera port). It runs on Android 17 without framework patches: it already uses the
A17 `StreamConfigurationMap` and `CaptureResultExtras` constructors.

The patched build (`leica-gauguin-en.apk`, release asset) changes:

| Change | How |
|---|---|
| gauguin profile (`xiaomi/xiaomi-mi-10t-lite-gauguin`, codes gauguin / M2007J17G/C/I; ultra + main + 2x; macro/depth as auxiliary) | `gauguin-profile.json`, added to `assets/device-profiles.json` |
| Auto-detect: `Profiles.init()` picks `Profiles.detected()` when nothing is selected | `patch_port.py` (smali) |
| Zoom chips 0.6 / 1 / 2 instead of 0.6, 0.6, 0.9, 0.9, 1x (duplicate ultrawide id, macro and depth were listed) | profile + `ProfileRouter.logicalPaths()` patch so the 2x stop can be a crop of the main camera |
| Hide the "OEM model experiment" screen: it needs the Hexagon HTP (QNN), SM7225 has none | `patch_port.py` |
| English porter UI: 682 hard-coded strings in smali, 150 strings in `resources.arsc`, manifest labels, device catalogue names | `translations-en.json`, `smali_strings.py`, `arsc_strings.py`, `arsc-translations-en.json` |

M9 / Full M9 styles already fall back to CPU / ONNX Runtime on devices without HTP; nothing
was forced.

Verified: 1x 3472x4624, 0.6x 2448x3264 (ultrawide), 2x 3472x4624; the profile is selected
on first launch. Known issue: one ANR when switching lens right after capture under debug
ART (eng build).

## Rebuild

Needs Java 17, Python 3, Android build-tools (zipalign, apksigner) and
`tools/bin/{smali,baksmali}.jar` 2.5.2 next to this folder.

```powershell
powershell -ExecutionPolicy Bypass -File leica\scripts\build-leica-gauguin.ps1 <original-leica-port.apk>
```

The script signs with a locally generated test key (`keys/`, created on first run), so
the original app must be uninstalled first. The tool that translates the encrypted author
dialog is not published (it contains the app's own key); without it the build skips that
dialog and keeps its original text.
