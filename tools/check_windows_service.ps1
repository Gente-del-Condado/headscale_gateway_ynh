# Aceptación en un runner desechable o una VM indicada expresamente con -LocalLab.
# Los servicios y directorios de prueba tienen nombres únicos y se retiran al terminar.
param([Parameter(Mandatory=$true)][string]$Package,[Parameter(Mandatory=$true)][string]$Root,[switch]$LocalLab)
$ErrorActionPreference='Stop'
if (-not $LocalLab -and ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted')) { throw 'Se requiere el runner desechable de GitHub o -LocalLab en una VM de pruebas.' }
$name='HeadscaleGatewayTest'+$PID
$install=Join-Path $env:ProgramFiles ('Headscale Gateway Test '+$PID)
$data=Join-Path $env:ProgramData ('Headscale Gateway Test '+$PID)
$began=Get-Date
$listener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,0)
$listener.Start();$port=$listener.LocalEndpoint.Port;$listener.Stop()
$url="http://127.0.0.1:$port"
$credential=New-Object Management.Automation.PSCredential('lab-admin',(ConvertTo-SecureString 'fixture-password-12345' -AsPlainText -Force))
$script=Join-Path $PSScriptRoot '../packaging/windows/Install-Service.ps1'
foreach ($notice in @('LICENSE','NOTICE')) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('../'+$notice)) -Destination $Package }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../src/third_party') -Destination $Package -Recurse
function Wait-Panel {
    for ($i=0;$i -lt 90;$i++) {
        try { $r=Invoke-WebRequest "$url/admin/" -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { return } } catch {}
        Start-Sleep -Milliseconds 500
    }
    throw 'El servicio no abrió el panel local.'
}
function Login {
    $script:session=New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $script:auth=Invoke-RestMethod "$url/api/v1/auth/login" -Method Post -ContentType 'application/json' -Body '{"username":"lab-admin","password":"fixture-password-12345"}' -WebSession $script:session
}
# Comprueba primero que Windows puede cargar el ejecutable sin iniciar el motor.
& (Join-Path $Package 'headscale-gateway.exe') --help | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Windows no pudo cargar el ejecutable del Gateway.' }
Write-Host 'WINDOWS_EJECUTABLE_OK'
try {
    & $script -Source $Package -InstallDirectory $install -DataDirectory $data -ServiceName $name -Port $port -InitialAdministrator $credential -Confirm:$false
    Wait-Panel;Login
    $status=Invoke-RestMethod "$url/api/v1/status" -WebSession $session
    if (-not $status.setup_required -or $status.vpn_connected) { throw 'El nodo se conectó antes de confirmar el nombre.' }
    $headers=@{'X-CSRF-Token'=$auth.csrf}
    Invoke-RestMethod "$url/api/v1/config" -Method Put -ContentType 'application/json' -Body '{"changes":{"headscale.node_name":"windows-lab"}}' -WebSession $session -Headers $headers | Out-Null
    $keyPath=Join-Path $data 'gateway/master.key'
    foreach($rule in (Get-Acl -LiteralPath $keyPath).Access) {
        $sid=$rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
        if ($rule.AccessControlType -eq 'Allow' -and $sid -in @('S-1-1-0','S-1-5-11','S-1-5-32-545')) { throw 'La clave permite acceso a cuentas ajenas al servicio.' }
    }
    $key=Get-FileHash (Join-Path $data 'gateway/master.key')
    $marker=Join-Path $data 'gateway/fixture-data.txt'
    Set-Content -LiteralPath $marker -Value 'fixture-secret-preserved'
    $hash=Get-FileHash $marker
    & $script -Source $Package -InstallDirectory $install -DataDirectory $data -ServiceName $name -Port $port -Confirm:$false
    Wait-Panel;Login
    if ((Get-FileHash $marker).Hash -ne $hash.Hash -or (Get-FileHash (Join-Path $data 'gateway/master.key')).Hash -ne $key.Hash) { throw 'Se modificaron datos o secretos.' }
    $settings=Invoke-RestMethod "$url/api/v1/config" -WebSession $session
    if ($settings.'headscale.node_name' -ne 'windows-lab') { throw 'Se perdió la configuración al actualizar.' }
    $service=Get-CimInstance Win32_Service -Filter "Name='$name'"
    $previous=$service.ProcessId
    Stop-Process -Id $previous -Force
    Start-Sleep -Seconds 7
    Wait-Panel;Login
    $service=Get-CimInstance Win32_Service -Filter "Name='$name'"
    if ($service.ProcessId -eq $previous -or $service.State -ne 'Running') { throw 'No se recuperó automáticamente.' }
    $previous=$service.ProcessId
    Invoke-RestMethod "$url/api/v1/system/restart" -Method Post -ContentType 'application/json' -Body '{}' -WebSession $session -Headers @{'X-CSRF-Token'=$auth.csrf} | Out-Null
    Start-Sleep -Seconds 8
    Wait-Panel;Login
    $service=Get-CimInstance Win32_Service -Filter "Name='$name'"
    if ($service.ProcessId -eq $previous) { throw 'El reinicio del panel no pasó por SCM.' }
    $menu=Join-Path ([Environment]::GetFolderPath('CommonPrograms')) $name
    if (-not (Test-Path (Join-Path $menu 'Headscale Gateway.url'))) { throw 'Falta el acceso de Inicio.' }
    Write-Host 'WINDOWS_SCM_OK: instalación, actualización, datos, clave, configuración, recuperación y reinicio del panel.'
 } catch {
    $state=Get-CimInstance Win32_Service -Filter "Name='$name'" -ErrorAction SilentlyContinue
    if ($state) { Write-Host ('SCM_DIAGNOSTICO: '+($state | Select-Object State,ExitCode,ServiceSpecificExitCode,StartName,PathName | ConvertTo-Json -Compress)) }
    Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Service Control Manager';StartTime=$began} -MaxEvents 40 -ErrorAction SilentlyContinue | Where-Object {$_.Message.Contains($name)} | ForEach-Object { Write-Host ('SCM_EVENTO: '+$_.Id+' '+$_.Message) }
    Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName=$name;StartTime=$began} -MaxEvents 10 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ('INICIO_DIAGNOSTICO: '+$_.Message) }
    $log=Join-Path $data 'gateway/logs/gateway.log'
    if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Tail 25 | ForEach-Object { Write-Host ('GATEWAY_DIAGNOSTICO: '+($_ -replace 'fixture-password-12345','[contraseña de prueba]')) } }
    throw
} finally {
    if (Get-Service $name -ErrorAction SilentlyContinue) { Stop-Service $name -ErrorAction SilentlyContinue; & sc.exe delete $name | Out-Null }
    if ([Diagnostics.EventLog]::SourceExists($name)) { Remove-EventLog -Source $name }
    $menu=Join-Path ([Environment]::GetFolderPath('CommonPrograms')) $name
    if (Test-Path $menu) { Remove-Item -LiteralPath $menu -Recurse -Force }
    foreach ($fixture in @($install,$data)) { if (Test-Path -LiteralPath $fixture) { Remove-Item -LiteralPath $fixture -Recurse -Force } }
}
