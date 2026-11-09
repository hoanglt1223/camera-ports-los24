#!/usr/bin/env python3
"""Build the flashable zips from blobs/ and module/ into release-assets/.

  python tools/build-zips.py                 # Magisk module + recovery install/restore zips
  python tools/build-zips.py --framework PATH --fingerprint FP --incremental N
                                             # also the optional framework.jar module

Every blob is checked against blobs/manifest.json before packaging.
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "release-assets"
MAGISK_UPDATE_BINARY = """#!/sbin/sh
umask 022
ui_print() { echo "$1"; }
require_new_magisk() {
  ui_print "*******************************"
  ui_print " Please install Magisk v20.4+! "
  ui_print "*******************************"
  exit 1
}
OUTFD=$2
ZIPFILE=$3
mount /data 2>/dev/null
[ -f /data/adb/magisk/util_functions.sh ] || require_new_magisk
. /data/adb/magisk/util_functions.sh
[ $MAGISK_VER_CODE -lt 20400 ] && require_new_magisk
install_module
exit 0
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lf(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def add(z: zipfile.ZipFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 11, 9, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100000 | mode) << 16
    z.writestr(info, data)


def payload(z: zipfile.ZipFile, files: list, extra: dict) -> None:
    lines = []
    for f in files:
        blob = ROOT / "blobs" / f["path"]
        got = sha256(blob)
        if got != f["sha256"]:
            sys.exit(f"{blob}: sha256 {got} != manifest {f['sha256']}")
        add(z, f"payload/files/{f['path']}", blob.read_bytes())
        lines.append("|".join([f["path"], f["kind"], f["stock_sha256"] or "", f["sha256"], f["context"]]))
    add(z, "payload/files.txt", ("\n".join(lines) + "\n").encode())
    add(z, "payload/common.sh", lf(ROOT / "module/common.sh"))
    for name, data in extra.items():
        add(z, f"payload/{name}", data)


def meta_inf(z: zipfile.ZipFile, update_binary: bytes) -> None:
    add(z, "META-INF/com/google/android/update-binary", update_binary, 0o755)
    add(z, "META-INF/com/google/android/updater-script", b"#MAGISK\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--framework", type=Path)
    ap.add_argument("--fingerprint")
    ap.add_argument("--incremental")
    args = ap.parse_args()

    files = json.loads((ROOT / "blobs/manifest.json").read_text())["files"]
    OUT.mkdir(exist_ok=True)
    mg = ROOT / "module/magisk"

    out = OUT / "miuicamera-los24-gauguin-magisk.zip"
    with zipfile.ZipFile(out, "w") as z:
        meta_inf(z, MAGISK_UPDATE_BINARY.encode())
        add(z, "customize.sh", lf(mg / "customize.sh"))
        add(z, "module.prop", lf(mg / "module.prop"))
        payload(z, files, {n: lf(mg / n) for n in ("module.prop", "sepolicy.rule", "post-fs-data.sh")})
    print(out)

    for mode, name in (("install", "recovery"), ("restore", "recovery-restore")):
        out = OUT / f"miuicamera-los24-gauguin-{name}.zip"
        with zipfile.ZipFile(out, "w") as z:
            meta_inf(z, lf(ROOT / "module/recovery/update-binary"))
            payload(z, files, {"mode": mode.encode() + b"\n"})
        print(out)

    if args.framework:
        if not (args.fingerprint and args.incremental):
            sys.exit("--framework needs --fingerprint and --incremental of the build it came from")
        fw = ROOT / "module/framework-optional"
        script = lf(fw / "customize.sh").replace(b"@FINGERPRINT@", args.fingerprint.encode())
        script = script.replace(b"@INCREMENTAL@", args.incremental.encode())
        out = OUT / "framework-legacy-ctors-los24-gauguin-magisk.zip"
        with zipfile.ZipFile(out, "w") as z:
            meta_inf(z, MAGISK_UPDATE_BINARY.encode())
            add(z, "customize.sh", script)
            add(z, "module.prop", lf(fw / "module.prop"))
            add(z, "framework.jar", args.framework.read_bytes())
        print(out)


if __name__ == "__main__":
    main()
