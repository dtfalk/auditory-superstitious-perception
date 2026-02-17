Write-Host "Restoring normal system state..."

$projectRoot = Split-Path $PSScriptRoot -Parent
$normalizedProjectRoot = $projectRoot.TrimEnd('\').ToLower()

$stateFile = "$env:TEMP\experiment_service_state.json"

if (Test-Path $stateFile) {

    $serviceStates = Get-Content $stateFile | ConvertFrom-Json

    foreach ($svc in $serviceStates.PSObject.Properties.Name) {

        $mode = $serviceStates.$svc

        if ($mode) {

            switch ($mode) {
                "Auto" { Set-Service $svc -StartupType Automatic }
                "Manual" { Set-Service $svc -StartupType Manual }
                "Disabled" { Set-Service $svc -StartupType Disabled }
            }

            Start-Service $svc -ErrorAction SilentlyContinue
            Write-Host "$svc restored to $mode."
        }
    }
}
else {
    Write-Host "No saved service state found."
}

# Defender exclusion removal (safe normalization)

$existingExclusions = (Get-MpPreference).ExclusionPath
$normalizedExclusions = @()

foreach ($path in $existingExclusions) {
    if ($path) {
        $normalizedExclusions += $path.TrimEnd('\').ToLower()
    }
}

if ($normalizedExclusions -contains $normalizedProjectRoot) {
    Remove-MpPreference -ExclusionPath $projectRoot
    Write-Host "Defender exclusion removed."
}
else {
    Write-Host "Defender exclusion not found."
}

Write-Host "System restored."
