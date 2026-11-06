param(
    [switch]$SkipCheck,
    [string]$ProjectDir,
    [string]$Slug,
    [string]$CompFile,
    [string]$MixFile
)

$ErrorActionPreference = "Stop"
$Scripts = $PSScriptRoot
$Proj = Split-Path $Scripts -Parent
$HF = Join-Path $Proj "hyperframes-workspace"

$Cfg = Get-Content (Join-Path $Scripts "config.json") -Raw | ConvertFrom-Json
$FfmpegDir = $Cfg.ffmpeg_dir
if ($FfmpegDir -and (Test-Path $FfmpegDir)) {
    $env:PATH = "$FfmpegDir;$env:PATH"
    Write-Host "== FFmpeg no PATH: $FfmpegDir"
}

# Diretorio de saida do video por projeto (ex: projects/buldogue-ingles/output)
if ($ProjectDir) {
    $OutDir = Join-Path $ProjectDir "output"
} else {
    $OutDir = Join-Path $Proj "output"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Linka a composicao e o mix do projeto no workspace HyperFrames
if ($CompFile -and (Test-Path $CompFile)) {
    Copy-Item -LiteralPath $CompFile -Destination (Join-Path $HF "index.html") -Force
    Write-Host "== composicao linkeda: $CompFile -> $HF\index.html"
} else {
    Write-Host "== usando composicao existente em $HF\index.html"
}
if ($MixFile -and (Test-Path $MixFile)) {
    Copy-Item -LiteralPath $MixFile -Destination (Join-Path $HF "final_mix.m4a") -Force
    Write-Host "== mix linkado: $MixFile -> $HF\final_mix.m4a"
} else {
    Write-Host "== usando mix existente em $HF\final_mix.m4a"
}

Write-Host "== HyperFrames: $HF"
Push-Location $HF
try {
    if (-not $SkipCheck) {
        Write-Host "== npm run check"
        npm run check
        if ($LASTEXITCODE -ne 0) { throw "check falhou" }
    }

    Write-Host "== npm run render -- --workers 10"
    npm run render -- --workers 10
    if ($LASTEXITCODE -ne 0) { throw "render falhou" }
}
finally {
    Pop-Location
}

$mp4 = Get-ChildItem -Path $HF -Recurse -Filter *.mp4 -File |
    Where-Object { $_.FullName -notmatch "\\assets\\" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $mp4) { throw "nenhum MP4 encontrado apos o render" }

# Nome do arquivo baseado no slug do projeto (ex: buldogue-ingles.mp4)
if (-not $Slug) {
    if ($env:SLUG) { $Slug = $env:SLUG } else { $Slug = "video" }
}
$target = Join-Path $OutDir ("$Slug.mp4")
Copy-Item -LiteralPath $mp4.FullName -Destination $target -Force
Write-Host "== copiado para $target"

if ($ProjectDir) {
    python (Join-Path $Scripts "verify_output.py") --file $target --proj $ProjectDir
} else {
    python (Join-Path $Scripts "verify_output.py") --file $target
}

