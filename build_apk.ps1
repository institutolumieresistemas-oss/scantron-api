# Build and Sign Scantron-Mobil.apk
param(
    [string]$OutputDir = "C:\Users\LENOVO\Desktop"
)

$ErrorActionPreference = "Stop"

$sdkPath = "$env:LOCALAPPDATA\Android\Sdk"
$buildTools = "$sdkPath\build-tools\35.0.0"
$platformJar = "$sdkPath\platforms\android-35\android.jar"
$jdkPath = "C:\Program Files\Android\Android Studio\jbr"

$env:JAVA_HOME = $jdkPath
$aapt2 = "$buildTools\aapt2.exe"
$zipalign = "$buildTools\zipalign.exe"
$apksigner = "$buildTools\apksigner.bat"
$javac = "$jdkPath\bin\javac.exe"
$keytool = "$jdkPath\bin\keytool.exe"
$d8 = "$buildTools\d8.bat"

Write-Host "===> 1. Compilando recursos con aapt2..." -ForegroundColor Cyan
& $aapt2 compile --dir android_app\res -o android_app\compiled_res.zip

Write-Host "===> 2. Enlazando recursos..." -ForegroundColor Cyan
Remove-Item "android_app\base.apk", "android_app\aligned.apk" -ErrorAction SilentlyContinue
& $aapt2 link -I $platformJar android_app\compiled_res.zip --manifest android_app\AndroidManifest.xml --java android_app\gen -o android_app\base.apk --auto-add-overlay

Write-Host "===> 3. Compilando codigo Java..." -ForegroundColor Cyan
& $javac -source 8 -target 8 -cp $platformJar -d android_app\obj android_app\gen\com\lumiere\scantron\R.java android_app\src\com\lumiere\scantron\MainActivity.java

Write-Host "===> 4. Convirtiendo clases a DEX..." -ForegroundColor Cyan
$classFiles = (Get-ChildItem -Recurse android_app\obj -Filter "*.class").FullName
cmd.exe /c "`"$d8`" --lib `"$platformJar`" --output android_app $classFiles"

Write-Host "===> 5. Empaquetando assets y clases..." -ForegroundColor Cyan
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$archive = [System.IO.Compression.ZipFile]::Open((Resolve-Path "android_app\base.apk").Path, [System.IO.Compression.ZipArchiveMode]::Update)
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, (Resolve-Path "android_app\classes.dex").Path, "classes.dex")

$assetFiles = Get-ChildItem -Recurse "android_app\assets" -File
foreach ($file in $assetFiles) {
    $relative = "assets/" + ($file.FullName.Substring((Resolve-Path "android_app\assets").Path.Length + 1)).Replace("\", "/")
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $relative)
}
$archive.Dispose()

Write-Host "===> 6. Alineando APK (zipalign)..." -ForegroundColor Cyan
& $zipalign -f -p 4 "android_app\base.apk" "android_app\aligned.apk"

Write-Host "===> 7. Firmando APK (apksigner)..." -ForegroundColor Cyan
if (!(Test-Path "android_app\scantron.keystore")) {
    & $keytool -genkeypair -v -keystore "android_app\scantron.keystore" -alias scantron -keyalg RSA -keysize 2048 -validity 10000 -storepass 123456 -keypass 123456 -dname "CN=Scantron, OU=Lumiere, O=Lumiere, L=City, ST=State, C=US"
}

$destApk = Join-Path $OutputDir "Scantron-Mobil.apk"
cmd.exe /c "`"$apksigner`" sign --ks `"android_app\scantron.keystore`" --ks-pass pass:123456 --out `"$destApk`" `"android_app\aligned.apk`""

Write-Host "===> 8. Verificando APK..." -ForegroundColor Cyan
cmd.exe /c "`"$apksigner`" verify --verbose `"$destApk`""

Write-Host "`n[EXITO] APK generado en: $destApk" -ForegroundColor Green
