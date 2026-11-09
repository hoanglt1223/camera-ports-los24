#!/system/bin/sh
# Optional: replaces /system/framework/framework.jar with a build that carries the
# StreamConfigurationMap + CaptureResultExtras legacy constructors.
# The jar is only valid for the exact LineageOS build it was compiled from, so the
# installer refuses any other build fingerprint.
SKIPUNZIP=1
WANT_FP="@FINGERPRINT@"
WANT_INC="@INCREMENTAL@"

fp="$(getprop ro.system.build.fingerprint)"
inc="$(getprop ro.build.version.incremental)"
ui_print "- framework.jar legacy camera constructors (LineageOS 24, gauguin)"
if [ "$fp" != "$WANT_FP" ] || [ "$inc" != "$WANT_INC" ]; then
  ui_print "! This framework.jar was built for:"
  ui_print "!   $WANT_FP ($WANT_INC)"
  ui_print "! Your build is:"
  ui_print "!   $fp ($inc)"
  abort "! Mismatch: apply patches/framework/*.patch to your own tree instead."
fi
mkdir -p "$MODPATH/system/framework"
unzip -o "$ZIPFILE" module.prop -d "$MODPATH" >&2
unzip -o "$ZIPFILE" framework.jar -d "$MODPATH/system/framework" >&2 || abort "! extract failed"
set_perm "$MODPATH/system/framework/framework.jar" 0 0 0644 u:object_r:system_file:s0
ui_print "- Done. Reboot (first boot may take longer)."
