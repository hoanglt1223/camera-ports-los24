# Rebuild the Leica port for gauguin from the untouched original APK.
# Output: out\leica-gauguin-en.apk (English porter UI, gauguin lens profile, HTP experiment hidden).
# Needs: java 17, python 3, Android build-tools (zipalign, apksigner), tools\bin\{smali,baksmali}.jar.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$orig = if ($args[0]) { $args[0] } else { Join-Path $root 'leica-installed.apk' }  # original Leica Port 8.x APK
$bin = Join-Path $root 'tools\bin'
$work = Join-Path $root 'work\build'
$outDir = Join-Path $root 'out'
$keys = Join-Path $root 'keys'
$bt = Get-ChildItem "$env:LOCALAPPDATA\Android\Sdk\build-tools" | Sort-Object Name | Select-Object -Last 1 -ExpandProperty FullName
$dexes = 11, 15, 17, 19, 22, 23, 24, 25, 26, 29, 30, 31

function Run($exe, [string[]]$a) { & $exe @a; if ($LASTEXITCODE) { throw "$exe failed ($LASTEXITCODE)" } }

if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force $work, $outDir, $keys | Out-Null

Run python (@('-I', '-c', "import zipfile,sys;z=zipfile.ZipFile(sys.argv[1]);[z.extract(n,sys.argv[2]) for n in sys.argv[3:]]", $orig, "$work\in", 'assets/device-profiles.json', 'resources.arsc', 'assets/cameralook/author-notice.bin', 'AndroidManifest.xml') + ($dexes | ForEach-Object { "classes$_.dex" }))

# AuthorNotice.java (re-encrypts the porter's author dialog) is not published: it embeds the app's own key.
# Without it the author dialog keeps its original language.
$notice = Test-Path "$PSScriptRoot\AuthorNotice.java"
if ($notice) {
    Run java @("$PSScriptRoot\AuthorNotice.java", 'decrypt', "$work\in\assets\cameralook\author-notice.bin", "$work\notice.dex")
    Run java @('-jar', "$bin\baksmali.jar", 'd', "$work\notice.dex", '-o', "$work\smali\notice")
}
foreach ($i in $dexes) { Run java @('-jar', "$bin\baksmali.jar", 'd', "$work\in\classes$i.dex", '-o', "$work\smali\classes$i") }
Run python @('-I', "$PSScriptRoot\patch_port.py", "$work\smali", "$work\in\assets\device-profiles.json", "$work\device-profiles.json", "$work\in\resources.arsc", "$work\resources.arsc")

if ($notice) {
    Run java @('-jar', "$bin\smali.jar", 'a', '-a', '28', "$work\smali\notice", '-o', "$work\notice-en.dex")
    Run java @("$PSScriptRoot\AuthorNotice.java", 'encrypt', "$work\in\assets\cameralook\author-notice.bin", "$work\notice-en.dex", "$work\author-notice.bin")
}
Run python @('-I', "$PSScriptRoot\arsc_strings.py", 'manifest', "$work\in\AndroidManifest.xml", "$work\AndroidManifest.xml")
$repl = @("assets/device-profiles.json=$work\device-profiles.json", "resources.arsc=$work\resources.arsc", "AndroidManifest.xml=$work\AndroidManifest.xml")
if ($notice) { $repl += "assets/cameralook/author-notice.bin=$work\author-notice.bin" }
foreach ($i in $dexes) {
    Run java @('-jar', "$bin\smali.jar", 'a', '-a', '28', "$work\smali\classes$i", '-o', "$work\classes$i.dex")
    $repl += "classes$i.dex=$work\classes$i.dex"
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
$out = Join-Path $outDir 'leica-gauguin-en.apk'
Run "$bt\apksigner.bat" @('sign', '--ks', $ks, '--ks-key-alias', 'leica', '--ks-pass', "file:$passFile",
    '--v1-signing-enabled', 'true', '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'true', '--out', $out, "$work\aligned.apk")
Run "$bt\apksigner.bat" @('verify', $out)
Write-Host "Built $out"
