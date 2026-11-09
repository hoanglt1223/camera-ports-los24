# Binary and framework patches

All offsets are file offsets in the gauguin MIUI 14 blobs (identity-mapped `.text`). Every
patcher in `patches/blobs/` asserts the original bytes before writing, so it cannot silently
patch the wrong file. Hashes: [../blobs/HASHES.md](../blobs/HASHES.md).

## 1. Framework: legacy camera2 constructors (generic)

MIUI Camera 4.5 constructs hidden camera2 classes by reflection with signatures from
Android 10-13:

- `StreamConfigurationMap` 15-arg constructor, removed in Android 17. Without it the app
  cannot build its stream map and dies at start.
  `patches/framework/streamconfigurationmap-legacy-ctor.patch` adds the overload back and
  delegates to the current constructor.
- `CaptureResultExtras` 7-, 8- and 11-arg constructors. Without them MIUI's custom capture
  result path fails and the app saves the 720x960 preview frame instead of the full
  4624x3472 capture. `patches/framework/captureresultextras-legacy-ctor.patch`; missing
  fields default to "unknown" (`-1`, `false`, `0`).

Alternative for the first one without a ROM rebuild: the LSPosed shim in `compat/xposed/`.
It needs Zygisk, and Zygisk injection into the camera process broke the vendor linker
namespace for MIVI on this device, so the framework patch is the recommended route.

## 2. SELinux: MIVI vendor libs

MIUI Camera (`priv_app`) `dlopen`s `/vendor/lib64/libmialgoengine.so` and friends:

```
allow priv_app vendor_file file { read open getattr execute map }
allow priv_app vendor_file lnk_file { read open getattr }
```

Shipped in the Magisk module (`sepolicy.rule` and a live `magiskpolicy` fallback). For a ROM,
add it to device sepolicy.

## 3. libcamera_dirty.so: camera provider SIGSEGV

`/vendor/lib64/libcamera_dirty.so` is Xiaomi dirty-lens detection with an embedded NN
runtime. Its NEON GEMM kernel loads a full 32-byte vector for the row tail, reading up to
32 bytes past a heap tensor. Under the MIUI camera's heap layout the tensor ends at a scudo
guard page, so `android.hardware.camera.provider@2.4-service_64` dies on preview.

Only `DirtyCamera::Forward` drives the NN runtime. Its first instruction becomes `ret`:

| Offset | Old | New |
|---|---|---|
| `0x7818` | `ff c3 03 d1` `sub sp, sp, #0xf0` | `c0 03 5f d6` `ret` |

`GetResult` ignores Forward's result; the zero-initialised probability keeps the verdict
"clean". Only loss: the "wipe your lens" hint. Patcher: `patch_libcamera_dirty.py apply|verify|revert`.

## 4. libcamera_algoup_jni / libcamera_mianode_jni: IProducerListener ABI

`getANativeWindow` in `/system/lib64/libcamera_algoup_jni.xiaomi.so` creates an A12-compiled
`SurfaceListener` (`BnInterface<IProducerListener>`) and passes it to `Surface::connect`.
A17 `BufferQueueProducer::connect` calls `asBinder(listener)` → the old
`queryLocalInterface` → `String16::size()` on the new String16 layout → SIGSEGV
(fault address is two ARM64 instruction words, a classic sign of reading code as data).

LineageOS 24 libgui handles a null listener on both `Surface::connect` and
`BufferQueueProducer::connect`, so the fix passes null and skips the matching `incStrong`:

| Lib | Offset | Old | New |
|---|---|---|---|
| algoup | `0x6230` | `str x22,[sp]` | `str xzr,[sp]` |
| algoup | `0x6234` | `cbz x22, 0x625c` | `b 0x625c` |
| mianode | `0xf15c` | `str x22,[sp]` | `str xzr,[sp]` |
| mianode | `0xf160` | `cbz x22, 0xf188` | `b 0xf188` |

The post-call `decStrong` is already null-guarded, so refcounts stay balanced. Only the
buffer listener callbacks for that surface are lost. mianode has the same code but was not
seen crashing; it is patched preventively.

## 5. com.vidhance.node.eis.so: video EIS heap overflow

Recording with EIS crashed the provider on the first frame, inside libvidhance, at a different
bad pointer every run. The real bug is in the CHI node: it does
`posix_memalign(&p, 8, 0x100)` and then calls libui's `GraphicBuffer` constructor on it.
`0x100` was `sizeof(GraphicBuffer)` in the Android 11/12 headers; the A17 class is about
`0xd30`, so every wrapped buffer overruns the heap by ~3 KB and corrupts libvidhance's objects.

Three sites, each `mov w2,#0x100` (`02208052`) → `mov w2,#0x1000` (`02008252`):
`0x2369c`, `0x2cc24`, `0x2d16c`. Script: `patch-vidhance-node-graphicbuffer-size.py in out`.

Stock `gralloc.lito.so` from MIUI 14 is part of the tested video setup and is shipped in the
packages.

## 6. com.vidhance.node.eis.so: NV12/NV21 colour swap

With Vidhance bypassed (`vendor.vidhance.enabled=0`) the node copies NV12 input to NV21
output with plain `memcpy`, so U and V are swapped (blue looks red). Both `bl memcpy` sites
(`0x128fc` whole-plane, `0x12a04` row-by-row) jump to code caves at `0x3f9a0`/`0x3f9c8`
(zero padding at the end of the RX segment, whose `p_filesz`/`p_memsz` grow to `0x2f000`).
For the chroma plane, when input and output formats differ, the cave copies with
`dst+1, size-1`. Script: `patch-vidhance-node-nv21-copy.py in out` (needs `keystone-engine`).

With the GraphicBuffer fix EIS works again, so this path only runs for a couple of startup
frames, but the patch is kept so colours stay correct if Vidhance is disabled.

Shipped blob = stock → nv21-copy → graphicbuffer-size (the two touch different offsets).

## 7. Scanning other blobs

`tools/scan-framework-ctor-allocs.py <dir>...` resolves PLT stubs, finds every `bl` to an
imported constructor of a libui/libgui/libbinder/libutils class, walks back to the nearest
`operator new`/`malloc`/`posix_memalign` and prints the size. On gauguin it found only the
Vidhance node; the A17-built libs allocate `GraphicBuffer` with `0xd30`, which is the
reference to compare against. 32-bit blobs were not scanned.
