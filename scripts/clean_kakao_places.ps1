$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$cleaner = Join-Path $PSScriptRoot "clean_kakao_places.py"
$environmentName = "afterglow-data-clean"

$condaCandidates = @(
    (Get-Command conda.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Join-Path $env:USERPROFILE "miniconda3\Scripts\conda.exe"),
    (Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe"),
    (Join-Path $env:LOCALAPPDATA "miniconda3\Scripts\conda.exe"),
    (Join-Path $env:LOCALAPPDATA "anaconda3\Scripts\conda.exe"),
    "C:\ProgramData\miniconda3\Scripts\conda.exe",
    "C:\ProgramData\anaconda3\Scripts\conda.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

if (-not $condaCandidates) {
    throw "Conda was not found. Install Miniconda/Anaconda or add conda.exe to PATH."
}

$conda = $condaCandidates[0]
$environmentExists = (& $conda env list --json | ConvertFrom-Json).envs |
    Where-Object { (Split-Path $_ -Leaf) -eq $environmentName }

if (-not $environmentExists) {
    & $conda create --name $environmentName --override-channels --channel conda-forge "python=3.12" --yes

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to prepare Conda environment."
    }
}

Push-Location $projectRoot
try {
    & $conda run --name $environmentName python $cleaner @args
    if ($LASTEXITCODE -ne 0) {
        throw "Cleaning failed."
    }
} finally {
    Pop-Location
}
