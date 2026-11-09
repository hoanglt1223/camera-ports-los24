#!/system/bin/sh
# Magisk / KernelSU installer. Verifies device and every stock blob before installing.
SKIPUNZIP=1

PAYLOAD="$TMPDIR/payload"
PLAN="$TMPDIR/plan.txt"
say() { ui_print "$1"; }
die() { ui_print "! $1"; abort "! Aborted, nothing was installed."; }
target_of() { echo "/$1"; }

mkdir -p "$PAYLOAD"
unzip -o "$ZIPFILE" 'payload/*' -d "$TMPDIR" >&2 || abort "! Cannot extract payload"
. "$PAYLOAD/common.sh"

say "- MIUI Camera port blobs for LineageOS 24 ($DEVICE)"
check_device
: > "$PLAN"
plan_files

# Files already patched on the base system are still added, so a module
# update never drops a file that only the previous module version provided.
while IFS='|' read -r rel kind stock want ctx; do
  [ -z "$rel" ] && continue
  case "$rel" in
    system/*) out="$MODPATH/$rel" ;;
    *) out="$MODPATH/system/$rel" ;;
  esac
  mkdir -p "$(dirname "$out")"
  cp -f "$PAYLOAD/files/$rel" "$out" || abort "! copy failed: $rel"
  set_perm "$out" 0 0 0644 "$ctx"
done < "$PAYLOAD/files.txt"

cp -f "$PAYLOAD/module.prop" "$MODPATH/module.prop"
cp -f "$PAYLOAD/sepolicy.rule" "$MODPATH/sepolicy.rule"
cp -f "$PAYLOAD/post-fs-data.sh" "$MODPATH/post-fs-data.sh"
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
say "- Done. Reboot, then open MIUI Camera."
