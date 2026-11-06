# Verificar as informações dos projetos recentes
$projects = Get-ChildItem "C:\videomaker\projects" -Directory | Select-Object -First 8

foreach ($proj in $projects) {
    $project_path = $proj.FullName
    if (Test-Path "$project_path\project-control.json") {
        $pc = Get-Content "$project_path\project-control.json" | ConvertFrom-Json
        $desc_length = $pc.publish.description.Length
        $title_length = $pc.publish.title.Length
        Write-Host "=== $($proj.Name) ==="
        Write-Host "Título length: $title_length caracteres"
        Write-Host "Descrição length: $desc_length caracteres"
        if ($desc_length -gt 0) {
            $desc_preview = $pc.publish.description.Substring(0, 200)
            Write-Host "Descrição preview: $desc_preview..."
        }
        Write-Host ""
    } else {
        Write-Host "=== $($proj.Name) ==="
        Write-Host "AVISO: project-control.json não encontrado"
    }
}