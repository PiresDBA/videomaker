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

# ---------------------------------------------------------------------------
# TRAVA DE IDIOMA (bug 2026-11-16)
# O video PT acabou renderizado com o MIX ES e o EN/ES com a composicao PT:
# os 3 MP4s sairam identicos. A causa foi renderizar direto, passando
# composicao/mix ja prontos de OUTRO idioma. Aqui o render aborta se:
#   - a composicao e o mix forem de idiomas diferentes; ou
#   - o slug do video (_pt/_en/_es) nao bater com o idioma da composicao/mix.
# Nao contorna: se a trava falhar, o problema e a composicao/mix - refaca.
# ---------------------------------------------------------------------------
function Get-CompLang([string]$file) {
    if (-not $file -or -not (Test-Path $file)) { return $null }
    $sidecar = "$file.lang"
    if (Test-Path $sidecar) { return ((Get-Content $sidecar -Raw).Trim().ToLower()) }
    $html = Get-Content $file -Raw
    if ($html -match 'data-lang="([a-z]{2})"') { return $Matches[1].ToLower() }
    return $null
}
function Get-MixLang([string]$file) {
    if (-not $file -or -not (Test-Path $file)) { return $null }
    $sidecar = "$file.lang"
    if (Test-Path $sidecar) { return ((Get-Content $sidecar -Raw).Trim().ToLower()) }
    return $null
}

$expectedLang = $null
if ($Slug -and ($Slug -match "_(pt|en|es)$")) { $expectedLang = $Matches[1].ToLower() }
$compLang = Get-CompLang $CompFile
$mixLang = Get-MixLang $MixFile

if ($compLang -and $mixLang -and $compLang -ne $mixLang) {
    throw ("IDIOMA ERRADO: composicao='$compLang' mas mix='$mixLang'. " +
           "Refaca o compose e o mix do MESMO idioma antes de renderizar.")
}
if ($expectedLang) {
    if ($compLang -and $compLang -ne $expectedLang) {
        throw ("IDIOMA ERRADO: video '$Slug' precisa de composicao '$expectedLang', " +
               "mas a composicao e '$compLang'.")
    }
    if ($mixLang -and $mixLang -ne $expectedLang) {
        throw ("IDIOMA ERRADO: video '$Slug' precisa de mix '$expectedLang', " +
               "mas o mix e '$mixLang'.")
    }
}
$videoLang = $expectedLang
if (-not $videoLang) { $videoLang = $compLang }
if (-not $videoLang) { $videoLang = $mixLang }
if (-not $videoLang) { $videoLang = "pt" }
Write-Host "== trava de idioma: video=$videoLang composicao=$compLang mix=$mixLang"

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
    # Musica dos primeiros 8s (junta com o intro dublado)
    $IntroMusic = Join-Path (Split-Path $MixFile -Parent) "intro_music.m4a"
    if (Test-Path $IntroMusic) {
        Copy-Item -LiteralPath $IntroMusic -Destination (Join-Path $HF "intro_music.m4a") -Force
        Write-Host "== intro_music linkado -> $HF\intro_music.m4a"
    }
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

# Ficha do video renderizado: qual idioma, qual composicao, qual mix.
# O check_video_idioma.py usa isto para garantir que o video _es foi mesmo
# renderizado em ES (e nao com o conteudo de outro idioma).
$meta = [ordered]@{
    slug        = $Slug
    lang        = $videoLang
    composicao  = $CompFile
    mix         = $MixFile
    rendered_at = (Get-Date).ToString("s")
    sha256      = (Get-FileHash $target -Algorithm SHA256).Hash
    size_bytes  = (Get-Item $target).Length
}
$metaJson = $meta | ConvertTo-Json
$metaPath = "$target.meta.json"
[System.IO.File]::WriteAllText($metaPath, $metaJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "== ficha do video: $metaPath (idioma=$videoLang)"

if ($ProjectDir) {
    python (Join-Path $Scripts "verify_output.py") --file $target --proj $ProjectDir
} else {
    python (Join-Path $Scripts "verify_output.py") --file $target
}

