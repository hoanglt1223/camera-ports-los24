# Rebuild the Leica port for gauguin from the untouched original APK.
# Output: out\leica-gauguin-en.apk (English porter UI, gauguin lens profile, HTP experiment hidden,
# lens-switch lock fix, Leica Styles entry after relaunch, 8 film-look LUT styles from film_luts.py).
# -Slim: out\leica-gauguin-en-slim.apk without assets gauguin (SM7225, no HTP) cannot use: the hidden
# legend85 QNN/HTP experiment, the Hexagon HTP V79/V81 dsp/ skeletons, the third leica-v4 model copy
# (donor120 reads lm_leica-v4 instead, see slim_patch.py) and resource locales other than en/vi/zh-CN.
# Needs: java 17 (javac), python 3, Android SDK platform android.jar + build-tools (zipalign, apksigner, aapt2, d8), Pillow, tools\bin\{smali,baksmali}.jar.
param([string]$Apk, [switch]$Slim)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$orig = if ($Apk) { $Apk } else { Join-Path $root 'leica-installed.apk' }  # original Leica Port 8.x APK
$bin = Join-Path $root 'tools\bin'
$work = Join-Path $root 'work\build'
$outDir = Join-Path $root 'out'
$keys = Join-Path $root 'keys'
$bt = Get-ChildItem "$env:LOCALAPPDATA\Android\Sdk\build-tools" | Sort-Object Name | Select-Object -Last 1 -ExpandProperty FullName
$dexes = 11, 15, 17, 19, 22, 23, 24, 25, 26, 29, 30, 31

function Run($exe, [string[]]$a) { & $exe @a; if ($LASTEXITCODE) { throw "$exe failed ($LASTEXITCODE)" } }

if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force $work, $outDir, $keys | Out-Null

Run python (@('-I', '-c', "import zipfile,sys;z=zipfile.ZipFile(sys.argv[1]);[z.extract(n,sys.argv[2]) for n in sys.argv[3:]]", $orig, "$work\in", 'assets/device-profiles.json', 'resources.arsc', 'assets/cameralook/author-notice.bin', 'AndroidManifest.xml', 'classes3.dex') + ($dexes | ForEach-Object { "classes$_.dex" }))

# AuthorNotice.java (re-encrypts the porter's author dialog) is not published: it embeds the app's own key.
# Without it the author dialog keeps its original language.
$notice = Test-Path "$PSScriptRoot\AuthorNotice.java"
if ($notice) {
    Run java @("$PSScriptRoot\AuthorNotice.java", 'decrypt', "$work\in\assets\cameralook\author-notice.bin", "$work\notice.dex")
    Run java @('-jar', "$bin\baksmali.jar", 'd', "$work\notice.dex", '-o', "$work\smali\notice")
}
foreach ($i in $dexes) { Run java @('-jar', "$bin\baksmali.jar", 'd', "$work\in\classes$i.dex", '-o', "$work\smali\classes$i") }
Run python @('-I', "$PSScriptRoot\patch_port.py", "$work\smali", "$work\in\assets\device-profiles.json", "$work\device-profiles.json", "$work\in\resources.arsc", "$work\resources.arsc")
if ($Slim) { Run python @('-I', "$PSScriptRoot\slim_patch.py", "$work\smali") }

# Fixes: lens-switch lock (MethodCache), Leica Styles entry after relaunch (classes3), film LUT styles.
$android = Get-ChildItem "$env:LOCALAPPDATA\Android\Sdk\platforms\*\android.jar" | Sort-Object FullName | Select-Object -Last 1 -ExpandProperty FullName
$javaSrc = Get-ChildItem -Recurse "$PSScriptRoot\java\src" -Filter *.java | ForEach-Object FullName
Run javac (@('--release', '8', '-nowarn', '-cp', "$android;$PSScriptRoot\java\stub", '-d', "$work\java-classes") + $javaSrc)
$javaClasses = Get-ChildItem -Recurse "$work\java-classes\com\codex\filmlut", "$work\java-classes\com\codex\rearlens" -Filter *.class | ForEach-Object FullName
New-Item -ItemType Directory -Force "$work\java-dex" | Out-Null
Run "$bt\d8.bat" (@('--release', '--min-api', '28', '--lib', $android, '--output', "$work\java-dex") + $javaClasses)
Run java @('-jar', "$bin\baksmali.jar", 'd', "$work\java-dex\classes.dex", '-o', "$work\java-smali")
Run java @('-jar', "$bin\baksmali.jar", 'd', "$work\in\classes3.dex", '-o', "$work\smali3")
Run python @('-I', "$PSScriptRoot\fixes_patch.py", "$work\smali", "$work\smali3", "$work\java-smali")
Run java @('-jar', "$bin\smali.jar", 'a', '-a', '28', "$work\smali3", '-o', "$work\classes3.dex")
Run python @('-I', "$PSScriptRoot\film_luts.py", "$work\film", "$PSScriptRoot\film-sample.jpg")

if ($notice) {
    Run java @('-jar', "$bin\smali.jar", 'a', '-a', '28', "$work\smali\notice", '-o', "$work\notice-en.dex")
    Run java @("$PSScriptRoot\AuthorNotice.java", 'encrypt', "$work\in\assets\cameralook\author-notice.bin", "$work\notice-en.dex", "$work\author-notice.bin")
}
Run python @('-I', "$PSScriptRoot\arsc_strings.py", 'manifest', "$work\in\AndroidManifest.xml", "$work\AndroidManifest.xml")
$arsc = "$work\resources.arsc"
if ($Slim) {
    Run python @('-I', '-c', "import zipfile,sys;z=zipfile.ZipFile(sys.argv[1],'w');z.write(sys.argv[2],'AndroidManifest.xml',8);z.write(sys.argv[3],'resources.arsc',0)", "$work\tables.apk", "$work\AndroidManifest.xml", "$work\resources.arsc")
    Run "$bt\aapt2.exe" @('optimize', '-c', 'en,vi,zh-rCN', '-o', "$work\tables-opt.apk", "$work\tables.apk")
    Run python @('-I', '-c', "import zipfile,sys;open(sys.argv[2],'wb').write(zipfile.ZipFile(sys.argv[1]).read('resources.arsc'))", "$work\tables-opt.apk", "$work\resources-slim.arsc")
    $arsc = "$work\resources-slim.arsc"
}
$repl = @("classes3.dex=$work\classes3.dex", "assets/device-profiles.json=$work\device-profiles.json", "resources.arsc=$arsc", "AndroidManifest.xml=$work\AndroidManifest.xml")
if ($notice) { $repl += "assets/cameralook/author-notice.bin=$work\author-notice.bin" }
foreach ($i in $dexes) {
    Run java @('-jar', "$bin\smali.jar", 'a', '-a', '28', "$work\smali\classes$i", '-o', "$work\classes$i.dex")
    $repl += "classes$i.dex=$work\classes$i.dex"
}
$repl += Get-ChildItem -Recurse "$work\film" -File | ForEach-Object { "--add=assets/$($_.FullName.Substring("$work\film\".Length).Replace('\', '/'))=$($_.FullName)" }
if ($Slim) {
    $repl += 'assets/legend85-experiment/', 'assets/donor120/leica-v4/', 'assets/leica-v4/dsp/', 'assets/lm_leica-v4/dsp/' | ForEach-Object { "--drop=$_" }
}
Run python (@('-I', "$PSScriptRoot\repack_apk.py", $orig, "$work\unsigned.apk") + $repl)
Run "$bt\zipalign.exe" @('-f', '-p', '4', "$work\unsigned.apk", "$work\aligned.apk")

$ks = Join-Path $keys 'leica-gauguin-test.jks'
$passFile = Join-Path $keys 'keystore.pass'
if (-not (Test-Path $ks)) {
    $pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    [IO.File]::WriteAllText($passFile, $pw)
    Run keytool @('-genkeypair', '-keystore', $ks, '-alias', 'leica', '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
        '-dname', 'CN=gauguin test', '-storepass:file', $passFile, '-keypass:file', $passFile)
}
$out = Join-Path $outDir $(if ($Slim) { 'leica-gauguin-en-slim.apk' } else { 'leica-gauguin-en.apk' })
Run "$bt\apksigner.bat" @('sign', '--ks', $ks, '--ks-key-alias', 'leica', '--ks-pass', "file:$passFile",
    '--v1-signing-enabled', 'true', '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'true', '--out', $out, "$work\aligned.apk")
Run "$bt\apksigner.bat" @('verify', $out)
Write-Host "Built $out"
