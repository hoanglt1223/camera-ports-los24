# Shared install logic for the Magisk module and the recovery zip.
# Sourced by module/magisk/customize.sh and module/recovery/update-binary.
# Needs: say <msg>, die <msg>, target_of <relpath> (prints the on-device path), $PAYLOAD.
# files.txt line format: relpath|kind|stock_sha256|sha256|context

DEVICE=gauguin

sha_of() { [ -f "$1" ] && sha256sum "$1" | cut -d' ' -f1; }

check_device() {
  dev="$(getprop ro.product.device 2>/dev/null)"
  [ -z "$dev" ] && dev="$(getprop ro.build.product 2>/dev/null)"
  [ "$dev" = "$DEVICE" ] || die "This package is for $DEVICE only (found '$dev')."
}

# Prints one action per file: "install|<relpath>" or "skip|<relpath>". Aborts on unknown blobs.
plan_files() {
  while IFS='|' read -r rel kind stock want ctx; do
    [ -z "$rel" ] && continue
    dst="$(target_of "$rel")"
    cur="$(sha_of "$dst")"
    if [ "$cur" = "$want" ]; then
      say "  = $rel (already in place)"
      echo "skip|$rel" >> "$PLAN"
    elif [ "$kind" = stock ]; then
      say "  + $rel (replace ${cur:-missing} with stock MIUI copy)"
      echo "install|$rel" >> "$PLAN"
    elif [ -z "$cur" ]; then
      die "$rel is missing on this device. Is the MIUI camera blob set installed?"
    elif [ "$cur" = "$stock" ]; then
      say "  + $rel (stock blob verified)"
      echo "install|$rel" >> "$PLAN"
    else
      die "$rel has unexpected SHA-256 $cur (expected stock $stock). Not touching it."
    fi
  done < "$PAYLOAD/files.txt"
}

entry_of() { grep "^$1|" "$PAYLOAD/files.txt"; }
