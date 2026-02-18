Write-Host "Entering experiment mode..."

$projectRoot = Split-Path $PSScriptRoot -Parent
$normalizedProjectRoot = $projectRoot.TrimEnd('\').ToLower()

Write-Host "Project root detected as:"
Write-Host "  $projectRoot"

$services = @("SysMain","WSearch","wuauserv")
$serviceStates = @{}

foreach ($svc in $services) {

    $service = Get-CimInstance Win32_Service -Filter "Name='$svc'" -ErrorAction SilentlyContinue

    if ($service) {

        $serviceStates[$svc] = $service.StartMode

        Stop-Service $svc -ErrorAction SilentlyContinue
        Set-Service $svc -StartupType Disabled

        Write-Host "$svc stopped and disabled."
    }
    else {
        Write-Host "$svc not found on this system."
    }
}

$serviceStates | ConvertTo-Json | Out-File "$env:TEMP\experiment_service_state.json"

# Defender exclusion
# Does not seem to work
# $existingExclusions = (Get-MpPreference).ExclusionPath
# $normalizedExclusions = @()

# foreach ($path in $existingExclusions) {
#     if ($path) {
#         $normalizedExclusions += $path.TrimEnd('\').ToLower()
#     }
# }
# 
# if ($normalizedExclusions -notcontains $normalizedProjectRoot) {
#     Add-MpPreference -ExclusionPath $projectRoot
#     Write-Host "Defender exclusion added for project root."
# }
# else {
#     Write-Host "Defender exclusion already exists."
# }

powercfg -setactive SCHEME_MIN
powercfg -change -standby-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0

Write-Host "Experiment mode enabled."
