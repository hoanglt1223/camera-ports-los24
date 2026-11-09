#!/system/bin/sh
# Lets MIUI Camera (priv_app) load the MIVI algo libs from /vendor. sepolicy.rule
# carries the same rules but is skipped when Magisk cannot find a preinit
# partition, so apply them live as well. Harmless if the ROM already has them.
command -v magiskpolicy >/dev/null 2>&1 || exit 0
magiskpolicy --live "allow priv_app vendor_file file { read open getattr execute map }"
magiskpolicy --live "allow priv_app vendor_file lnk_file { read open getattr }"
