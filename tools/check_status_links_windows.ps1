# Edge usa un perfil temporal y comunica un resultado mínimo por loopback.
param([Parameter(Mandatory=$true)][string]$Fixture,[Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference='Stop'
$candidates=@((Join-Path ${env:ProgramFiles(x86)} 'Microsoft/Edge/Application/msedge.exe'),(Join-Path $env:ProgramFiles 'Microsoft/Edge/Application/msedge.exe'))
$edge=$candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if(-not $edge){throw 'Se necesita Microsoft Edge instalado para comprobar el panel en Windows.'}
$page=Join-Path $Fixture 'index.html'
if(-not (Test-Path -LiteralPath $page)){throw 'No existe la página de laboratorio.'}
$profile=Join-Path $Root ('edge-status-'+[guid]::NewGuid())
$socket=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,0)
$socket.Start();$port=$socket.LocalEndpoint.Port;$socket.Stop()
$prefix='http://127.0.0.1:'+ $port +'/'+[guid]::NewGuid().ToString()+'/'
$listener=New-Object Net.HttpListener
$listener.Prefixes.Add($prefix)
$process=$null
try {
    $listener.Start()
    $uri=([Uri]([IO.Path]::GetFullPath($page))).AbsoluteUri+'#report='+[Uri]::EscapeDataString($prefix+'result')
    $arguments=@('--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check','--disable-extensions','--no-proxy-server',('--user-data-dir="'+$profile+'"'),'--virtual-time-budget=3000',('"'+$uri+'"'))
    $waiting=$listener.GetContextAsync()
    $process=Start-Process -FilePath $edge -ArgumentList $arguments -PassThru
    if(-not $waiting.Wait(90000)){throw ('Edge no entregó el resultado en 90 segundos. Versión: '+[Diagnostics.FileVersionInfo]::GetVersionInfo($edge).FileVersion)}
    $context=$waiting.Result
    $result=$context.Request.QueryString['result']
    $context.Response.StatusCode=204;$context.Response.Close()
    if($result -notlike 'STATUS_LINKS_BROWSER_OK:*'){throw ('El navegador rechazó la prueba: '+$result)}
    Write-Host 'ENLACES_WINDOWS_OK: Edge real, dominio principal, HTTPS/HTTP, foco conservado y navegación fuera del panel.'
} finally {
    $listener.Close()
    # Solo procesos con el directorio GUID creado para este ensayo, nunca el
    # perfil normal ni otras ventanas de Edge del usuario.
    Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($profile) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    if($process){$process.Dispose()}
    if(Test-Path -LiteralPath $profile){Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue}
}
