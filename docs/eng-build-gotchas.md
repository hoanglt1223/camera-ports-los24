# Eng-build gotchas when testing camera ports

The test ROM was an `eng` build (`ro.build.type=eng`). Eng builds change runtime behaviour in
ways that make large ported apps (MIUI Camera, the Leica port) look broken or extremely slow.
Test on `userdebug` if you can; if you must use eng, check these first.

| Symptom | Cause | Fix |
|---|---|---|
| Apps take seconds per screen, reflection-heavy code ANRs, dex runs interpreted | The eng build sets the ART compat override `OVERRIDE_DISABLE_DEXOPT_ALL`, so installed apps are never dexopted | Build `userdebug`, or compile the app by hand: `adb shell pm compile -m speed-profile -f <package>` (check with `dumpsys package <package>`, "compilation_filter") |
| Everything in ART is several times slower; one Leica ANR while a background thread held a class lock during `Method.getReturnType`/`TimSort` | Eng builds run the debug runtime `libartd.so` | `adb shell setprop persist.sys.dalvik.vm.lib.2 libart.so` and reboot (verify the app maps `libart.so`, not `libartd.so`, in `/proc/<pid>/maps`) |
| Old vendor/app JNI libs abort with `JNI DETECTED ERROR IN APPLICATION` | CheckJNI is on by default on eng | `adb shell setprop dalvik.vm.checkjni false` (and `ro.kernel.android.checkjni` is honoured at boot), then restart the app |

None of these are camera bugs; they only change timing and strictness. Re-test any "ANR" or
"JNI abort" after removing them before patching anything.
