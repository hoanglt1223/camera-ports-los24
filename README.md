# Camera ports for LineageOS 24 (Android 17) — Xiaomi gauguin

MIUI Camera 4.5, a Leica camera port and several GCam builds running on
**LineageOS 24 (Android 17)** on the **Xiaomi Mi 10T Lite 5G / Redmi Note 9 Pro 5G
(gauguin, SM7225 "lito")**.

The device files are specific to gauguin. The methods are not: old vendor and app
blobs built against Android 11/12 break on Android 17 in a few predictable ways, and
this repo documents how each one was found and fixed, so other device maintainers can
reuse it.

Tiếng Việt: [README.vi.md](README.vi.md)

## Status (verified 2026-11-09)

| App | Version | Photo | Video | Notes |
|---|---|---|---|---|
| MIUI Camera (`com.android.camera`) | 4.5.002030.1 (MIUI 14) | OK, full-res 4624x3472 | OK, 1080p with EIS | Needs the blob patches and the framework patches below |
| Leica port (`com.kobbin.leica.wmrebuild`) | 8.0.0 (port 8.x), patched build | OK, 3472x4624; ultrawide 2448x3264 | not tested | Best detail and colour in our tests |
| GCam MGC 9.8.102 (`com.android.MGC_9_8_102`) | 9.8.102 | OK | – | Balanced, clean |
| GCam LMC 8.4 R18F1 (`com.google.android.GoogleCameraEngR18F1`) | 8.4.300 | OK | – | Opens in Night Sight by default |
| GCam MGC 9.4.103 V41 BSG (`org.codeaurora.snapcam`) | 9.4.103 | OK | – | Lens chips 0.6 / 0.9 / 1.0 |
| GCam LMC 8.8 R2 | 8.8 | Preview only | – | Captures are not saved |
| GCam Urnyx 7.3 | 7.3 | – | – | Not usable: no launchable activity on Android 17 |
| Aperture (`org.lineageos.aperture`) | 17 | OK | OK | Noisiest images: no multi-frame processing |

Image quality, from one indoor test scene: Leica port best detail and colour, GCam (MGC)
balanced and clean, Aperture noisier, MIUI Camera now full resolution (it produced
720x960 preview frames before the CaptureResultExtras fix).

Sample photos: coming later.

### Known issues

- MIUI Camera: the 32-bit `mediaserver` crashes in `FrameDecoder` when it thumbnails a
  recorded mp4. The video file is still saved. After the first clip the record button
  sometimes ignores taps until the app is relaunched (probably the same cause, not confirmed).
- MIUI Camera: Xiaomi dirty-lens detection always reports "clean" (the inference that
  crashed the camera provider is disabled).
- Leica port: one ANR when switching lens right after a capture. Seen only under the
  debug ART runtime of an eng build (see [docs/eng-build-gotchas.md](docs/eng-build-gotchas.md)).

## What is in this repo

```
blobs/                  patched gauguin blobs + stock MIUI gralloc, laid out by device path
  manifest.json         stock SHA-256 -> patched SHA-256, SELinux context, patcher per file
  HASHES.md             same table, human readable
patches/framework/      frameworks/base patches: legacy camera2 constructors (generic)
patches/blobs/          reproducible binary patchers (they assert the original bytes)
tools/build-zips.py     builds the Magisk module and the recovery zips into release-assets/
tools/scan-framework-ctor-allocs.py   old-ABI framework object size scanner (generic)
module/                 installer scripts shared by the Magisk and recovery zips
compat/xposed/          LSPosed shim (StreamConfigurationMap ctor) - superseded by the framework patch
leica/scripts/          rebuild scripts for the patched Leica port
docs/                   patch write-ups and eng-build notes
```

## Install (gauguin, LineageOS 24)

Release assets (GitHub Releases, not in git):

| File | What |
|---|---|
| `miuicamera-los24-gauguin-magisk.zip` | Magisk / KernelSU module: patched blobs, stock gralloc, MIVI SELinux rule |
| `miuicamera-los24-gauguin-recovery.zip` | Same files written directly to system/vendor from LineageOS recovery |
| `miuicamera-los24-gauguin-recovery-restore.zip` | Puts the backed-up originals back |
| `framework-legacy-ctors-los24-gauguin-magisk.zip` | Optional: `framework.jar` with the legacy constructors. **Only for the identical build** `lineage_gauguin ... CP2A.260605.016` incremental `1794015279`; it refuses anything else |
| `leica-gauguin-en.apk` | Patched Leica port (532 MB) |

1. Install MIUI Camera 4.5.002030.1. It is not redistributed here: extract
   `/system/priv-app/MiuiCamera/` from the stock **MIUI 14.0.4.0 (SJSEUXM) gauguin** ROM,
   or use a public mirror of `com.android.camera` 4.5.002030.1 for gauguin.
   The ROM also has to ship the MIUI camera vendor blobs (MIVI `libmialgoengine.so` and
   friends) and the system-side `*.xiaomi.so` JNI libs.
2. Get the legacy constructors into the framework: apply `patches/framework/*.patch` to
   `frameworks/base` and rebuild, or, on the identical build only, flash the optional
   framework module.
3. Flash **one** of: the Magisk module, or the recovery zip.

Both installers check `ro.product.device == gauguin`, then hash every target file on the
device. A file is replaced only if its hash is the known stock hash (or already the patched
one). Anything else aborts with the path and the unexpected hash, before any file is written.
`gralloc.lito.so` is a full stock file, so it is replaced whatever its current hash is (and
backed up first in recovery).

The recovery zip backs originals up to `/data/media/0/camera-port-backup/` (falls back to
`<file>.camera-port.orig` next to the file if `/data` is not usable in recovery) and keeps
the SELinux context of each original. If system or vendor is read-only in recovery
(ext4 with `shared_blocks`), use the Magisk module instead.

To rebuild the zips: `python tools/build-zips.py` (add
`--framework <jar> --fingerprint <fp> --incremental <n>` for the optional module).

## The fixes

Details, disassembly and verification: [docs/binary-patches.md](docs/binary-patches.md).

| Symptom | Cause | Fix | Scope |
|---|---|---|---|
| MIUI Camera dies at start: `NoSuchMethodException StreamConfigurationMap.<init>` | Android 17 removed the 15-arg constructor that MIUI calls by reflection | `patches/framework/streamconfigurationmap-legacy-ctor.patch` (or the LSPosed shim) | Generic |
| MIUI photos come out 720x960 | MIUI builds `CaptureResultExtras` with an API 29-33 constructor; it fails and MIUI saves the preview frame | `patches/framework/captureresultextras-legacy-ctor.patch` | Generic |
| MIUI Camera cannot load MIVI (`dlopen libmialgoengine.so` denied) | `priv_app` may not read/execute `vendor_file` | SELinux rule (in the Magisk module, or bake into device sepolicy) | Device sepolicy |
| Camera provider SIGSEGV in `libcamera_dirty.so` on preview | Embedded NN GEMM kernel reads past a heap tensor that ends at a guard page | `DirtyCamera::Forward` returns immediately (dirty-lens hint disabled) | gauguin offsets |
| MIUI app SIGSEGV in `libcamera_algoup_jni.xiaomi.so` (`String16::size` via `queryLocalInterface`) | A12-compiled `IProducerListener` subclass passed into A17 libgui | Pass a null listener to `Surface::connect` | gauguin offsets |
| Same code in `libcamera_mianode_jni.xiaomi.so` | Same bug, not seen crashing yet | Same patch | gauguin offsets |
| Provider crashes on first video frame inside libvidhance, random bad pointers | `com.vidhance.node.eis.so` placement-constructs `GraphicBuffer` in 0x100 bytes; the A17 class is ~0xd30 | Grow the 3 allocations to 0x1000 | gauguin offsets |
| Video red/blue swapped with EIS bypassed | Vidhance node copies NV12 into NV21 with a plain memcpy | Code cave that shifts the chroma plane by one byte | gauguin offsets |

Leica port changes (gauguin lens profile with auto-detect, zoom chips 0.6 / 1 / 2, English
porter UI, HTP-only experiment screen hidden; M9 styles already run on CPU): see
[leica/README.md](leica/README.md).

## Generic Android: what carries over to other devices

Reusable as-is:

- **Framework legacy constructors** (`patches/framework/`). Any Android 14+ ROM running a
  MIUI/HyperOS-derived camera app built for Android 10-13 will hit the same reflection calls.
  The patches only add overloads that delegate to the current constructors.
- **The old-ABI method.** When an old blob crashes deep inside libgui/libui/libbinder with a
  different bad pointer each time, suspect a framework C++ object whose layout changed:
  1. Old code subclassing a framework interface (here `BnInterface<IProducerListener>`) and
     handing it to the new framework. Find where the object is passed and pass null if the
     framework accepts null (check the framework source for `!= nullptr` guards).
  2. Old code allocating a framework object itself (`posix_memalign`/`operator new` with the
     old `sizeof`) and calling the new constructor on it. The constructor then overruns the
     heap. `tools/scan-framework-ctor-allocs.py <dir>...` finds every imported framework ctor
     call and the size of the allocation in front of it (needs `pyelftools`, `capstone`).
     Compare the size with what an A17-built lib allocates for the same class.
- **Eng-build pitfalls** that make ported apps look broken: [docs/eng-build-gotchas.md](docs/eng-build-gotchas.md).

Device-specific: every offset in `patches/blobs/` and every blob in `blobs/`. The patchers
assert the exact original bytes, so on another device they refuse to run; use the write-ups
to find the equivalent sites in your blobs.

## Licence

Scripts and documentation: MIT ([LICENSE](LICENSE)). Binaries under `blobs/` and in the
release assets belong to Xiaomi, Qualcomm, Imint and their other owners and are provided
only for interoperability; see [NOTICE](NOTICE).
