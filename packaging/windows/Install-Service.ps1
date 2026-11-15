# Instala el motor como servicio nativo y crea el acceso al panel local.
# Autor: Gente del Condado · headscale-gateway@gentedelcondado.es
[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [string]$Source = $PSScriptRoot,
    [string]$InstallDirectory = "$env:ProgramFiles\Headscale Gateway",
    [string]$DataDirectory = "$env:ProgramData\Headscale Gateway",
    [ValidatePattern('^[A-Za-z0-9_-]{1,64}$')][string]$ServiceName = 'HeadscaleGateway',
    [ValidateRange(1024,65535)][int]$Port = 9091,
    [PSCredential]$InitialAdministrator
)
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Abre PowerShell como administrador para instalar el servicio.' }
$binary = Join-Path $Source 'headscale-gateway.exe'
if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw 'Extrae el paquete completo antes de ejecutar este instalador.' }
foreach ($name in @('LICENSE','NOTICE','third_party')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Source $name))) { throw 'Faltan licencias o avisos de terceros; extrae el paquete completo.' }
}
Write-Host 'Headscale Gateway - Gente del Condado'
Write-Host 'Se instalará como servicio automático con cuenta LocalService y reinicio tras fallo.'
Write-Host 'La administración será local. No se abren puertos del cortafuegos ni se instalan CA.'
Write-Host "Panel: http://127.0.0.1:$Port/admin/"
Write-Host 'Soporte: headscale-gateway@gentedelcondado.es'
Write-Host 'Manual: https://gente-del-condado.github.io/headscale_gateway_ynh/WINDOWS_SERVICIO.html'
if (-not $PSCmdlet.ShouldProcess($InstallDirectory, 'Instalar o actualizar el servicio y el acceso del menú Inicio')) { return }
if ([IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\') -eq [IO.Path]::GetFullPath($Source).TrimEnd('\')) { throw 'El origen debe ser distinto del directorio de instalación.' }
$config = Join-Path $DataDirectory 'config'
$state = Join-Path $DataDirectory 'gateway'
$startup = Join-Path $config 'startup.json'
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    $registered = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'"
    $expected = '"' + (Join-Path $InstallDirectory 'headscale-gateway.exe') + '" --windows-service ' + $ServiceName
    if (-not $registered.PathName.StartsWith($expected, [StringComparison]::OrdinalIgnoreCase) -or $registered.StartName -ne 'NT AUTHORITY\LocalService') { throw 'El nombre pertenece a otro servicio o cuenta; se requiere revisión antes de cambiarlo.' }
}
if (-not (Test-Path -LiteralPath $startup) -and (Test-Path -LiteralPath (Join-Path $state 'gateway.sqlite'))) { throw 'Datos previos sin contrato de arranque: se requiere migración explícita; no se sobrescriben.' }
if (-not (Test-Path -LiteralPath $startup) -and -not $InitialAdministrator) { $InitialAdministrator = Get-Credential -Message 'Cuenta inicial para el panel de Headscale Gateway (contraseña de 12 a 72 bytes)' }
# El estado Stopped puede llegar antes de que el proceso libere el ejecutable.
# Conserva su handle antes de detenerlo: no se espera a un PID reutilizado.
$oldProcess=$null
try {
    if ($existing -and $registered.ProcessId -gt 0) {
        $oldProcess=Get-Process -Id $registered.ProcessId -ErrorAction SilentlyContinue
        if ($oldProcess) { $null=$oldProcess.Handle }
    }
    if ($existing -and $existing.Status -ne 'Stopped') { Stop-Service $ServiceName; (Get-Service $ServiceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(40)) }
    if ($oldProcess -and -not $oldProcess.WaitForExit(40000)) { throw 'El proceso anterior no ha terminado; no se sustituye el ejecutable.' }
} finally { if ($oldProcess) { $oldProcess.Dispose() } }
New-Item -ItemType Directory -Force -Path $InstallDirectory,$config,$state | Out-Null
& icacls.exe $InstallDirectory /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX' '*S-1-5-32-545:(OI)(CI)RX' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudo proteger el directorio de ejecutables.' }
# (OI)(CI) se aplica a la raíz del árbol; los archivos heredan sus permisos.
# No se eliminan recursivamente las ACE heredadas de archivos existentes.
# SID invariantes: administradores, sistema y LocalService. Los secretos no son
# legibles por otras cuentas. No se pasan contraseñas en argumentos de procesos.
& icacls.exe $DataDirectory /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-19:(OI)(CI)M' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron proteger los datos; no se inicia el servicio.' }
foreach ($name in @('headscale-gateway.exe','hgw-ca-helper.exe','LICENSE','NOTICE','VERSION','LEEME_BINARIOS.txt')) {
    $file = Join-Path $Source $name
    if (Test-Path -LiteralPath $file -PathType Leaf) { Copy-Item -LiteralPath $file -Destination $InstallDirectory -Force }
}
Copy-Item -LiteralPath (Join-Path $Source 'third_party') -Destination $InstallDirectory -Recurse -Force
if (-not (Test-Path -LiteralPath $startup)) {
    if (-not $InitialAdministrator -or -not $InitialAdministrator.UserName.Trim()) { throw 'Falta la cuenta inicial.' }
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($InitialAdministrator.Password)
    try {
        $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        $length = [Text.Encoding]::UTF8.GetByteCount($password)
        if ($length -lt 12 -or $length -gt 72) { throw 'La contraseña debe tener de 12 a 72 bytes UTF-8.' }
        $initial = Join-Path $config 'initial-admin.json'
        $encoding = New-Object Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($initial, (@{username=$InitialAdministrator.UserName;password=$password} | ConvertTo-Json), $encoding)
        $node = ($env:COMPUTERNAME.ToLowerInvariant() -replace '[^a-z0-9-]','-' -replace '-+','-').Trim('-')
        if (-not $node) { $node = 'windows-device' }
        [IO.File]::WriteAllText($startup, (@{listen_addr="127.0.0.1:$Port";node_name=$node;initial_admin_file=$initial} | ConvertTo-Json), $encoding)
    } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer); $password=$null }
}
$targetBinary = Join-Path $InstallDirectory 'headscale-gateway.exe'
$command = '"' + $targetBinary + '" --windows-service ' + $ServiceName + ' --db "' + (Join-Path $state 'gateway.sqlite') + '"'
if (-not $existing) {
    $emptyPassword = New-Object Security.SecureString
    $localService = New-Object Management.Automation.PSCredential('NT AUTHORITY\LocalService', $emptyPassword)
    New-Service -Name $ServiceName -BinaryPathName $command -DisplayName 'Headscale Gateway' -Description 'Gente del Condado - headscale-gateway@gentedelcondado.es - https://gente-del-condado.github.io/headscale_gateway_ynh/' -StartupType Automatic -Credential $localService | Out-Null
} else {
    # CIM recibe la ruta como dato; evita que una shell nativa pierda sus comillas.
    $changed = Invoke-CimMethod -InputObject $registered -MethodName Change -Arguments @{PathName=$command;StartMode='Automatic'}
    if ($changed.ReturnValue -ne 0) { throw 'No se pudo actualizar el servicio.' }
}
Set-Service -Name $ServiceName -Description 'Gente del Condado - headscale-gateway@gentedelcondado.es - https://gente-del-condado.github.io/headscale_gateway_ynh/'
$registry = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
New-ItemProperty -Path $registry -Name Environment -PropertyType MultiString -Value @("GATEWAY_BOOTSTRAP_FILE=$startup") -Force | Out-Null
& sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/15000/restart/30000 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudo configurar la recuperación.' }
& sc.exe failureflag $ServiceName 1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudo activar la recuperación tras salida de servicio.' }
$menu = Join-Path ([Environment]::GetFolderPath('CommonPrograms')) $ServiceName
New-Item -ItemType Directory -Force -Path $menu | Out-Null
$effective = Get-Content -LiteralPath $startup -Raw | ConvertFrom-Json
$address = [Uri]("http://" + $effective.listen_addr + '/admin/')
if (-not $address.IsLoopback) { throw 'El acceso del menú solo admite administración loopback.' }
[IO.File]::WriteAllText((Join-Path $menu 'Headscale Gateway.url'), "[InternetShortcut]`r`nURL=$($address.AbsoluteUri)`r`n")
[IO.File]::WriteAllText((Join-Path $menu 'Manual de Headscale Gateway.url'), "[InternetShortcut]`r`nURL=https://gente-del-condado.github.io/headscale_gateway_ynh/`r`n")
# El registro de eventos conserva los fallos anteriores al registro de archivos.
if (-not [Diagnostics.EventLog]::SourceExists($ServiceName)) { New-EventLog -LogName Application -Source $ServiceName }
Start-Service $ServiceName
(Get-Service $ServiceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(40))
$ready=$false
for ($attempt=0;$attempt -lt 40;$attempt++) {
    try {
        $response=Invoke-WebRequest -Uri $address.AbsoluteUri -UseBasicParsing -MaximumRedirection 0 -TimeoutSec 2
        if ($response.StatusCode -eq 200 -and $response.Content.Contains('Headscale Gateway') -and (Get-Service $ServiceName).Status -eq 'Running') { $ready=$true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $ready) { throw 'El panel local no está listo. Se conservan los datos: revisa el servicio y los registros antes de continuar.' }
Write-Host 'SERVICIO_WINDOWS_CONFIGURADO_OK: cuenta LocalService, inicio automático y acceso del menú Inicio.'
Write-Host 'Los datos, las credenciales y la identidad se conservan al actualizar. Confirma el nombre propuesto desde el panel antes de conectar a Headscale.'
