package org.headscalegateway.android;

import android.content.Intent;
import android.content.Context;
import android.os.Build;
import android.net.VpnService;
import android.os.ParcelFileDescriptor;
import java.io.File;
import java.util.concurrent.*;

/** Adaptación del enfoque VpnService + HEV usado por TailSocks, con el nodo del Gateway. */
public final class GatewayVpnService extends VpnService {
    private static final String STOP="org.headscalegateway.android.STOP_VPN";
    static { System.loadLibrary("gateway-tunnel"); }
    static native int runTunnel(String config,int fd);
    static native void stopTunnel();
    static volatile boolean active=false;
    private ParcelFileDescriptor device;
    private volatile boolean stopping=false;
    private volatile String lastError="";
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    static void requestStop(Context context) {
        // Android mantiene enlazado VpnService mientras exista el túnel.
        // stopService por sí solo no invoca onDestroy en ese estado.
        String phase=RuntimeState.phoneVPN(context).optString("phase");
        Intent stop=new Intent(context,GatewayVpnService.class);
        if(!phase.equals("connected") && !phase.equals("starting")) {context.stopService(stop);return;}
        stop.setAction(STOP);
        if(Build.VERSION.SDK_INT>=26)context.startForegroundService(stop);else context.startService(stop);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        startForeground(11,GatewayService.notification(this,getString(R.string.vpn_active)));
        if(intent!=null && STOP.equals(intent.getAction())) {shutdown();return START_NOT_STICKY;}
        if(stopping)return START_NOT_STICKY;
        if(!active) { active=true; RuntimeState.phoneVPN(this,"starting","");worker.execute(this::connect); }
        return START_NOT_STICKY;
    }
    private void connect() {
        try {
            org.json.JSONObject state=RuntimeState.control(this,"/state");
            if(!state.optBoolean("connected")) throw new IllegalStateException(getString(R.string.vpn_pending));
            // El mismo nodo decide las rutas y el nodo de salida. Sin nodo de
            // salida, el adaptador utiliza la conexión habitual del dispositivo.
            Builder builder=new Builder().setSession(getString(R.string.app_name)).setMtu(1280)
                .addAddress("10.254.254.1",32).addAddress("fd00:6867:7700::1",128)
                .addDnsServer("100.100.100.100")
                .addDisallowedApplication(getPackageName());
            VpnRoutes.apply(this,builder,state.optBoolean("lan_bypass",true));
            synchronized(this) { if(stopping) return; device=builder.establish();if(device!=null)RuntimeState.phoneVPN(this,"connected",""); }
            if(device==null) throw new IllegalStateException(getString(R.string.vpn_revoked));
            File config=new File(RuntimeState.root(this),"tunnel.yaml");
            RuntimeState.write(config,"tunnel:\n  mtu: 1280\nsocks5:\n  address: '127.0.0.1'\n  port: "+RuntimeState.prefs(this).getInt("socks_port",0)
                +"\n  udp: 'udp'\n  username: 'gateway'\n  password: '"+RuntimeState.secret(this,"bridge_secret")+"'\n");
            int result=runTunnel(config.getPath(),device.getFd());
            if(result!=0 && !stopping)lastError="El túnel VPN se ha detenido.";
        } catch(Exception e) {lastError=getString(R.string.error,e.getMessage());}
        finally {active=false;shutdown();}
    }
    @Override public void onRevoke() { shutdown(); }
    private void finishProcess() {
        RuntimeState.phoneVPN(this,"stopped",lastError);
        android.os.Process.killProcess(android.os.Process.myPid());
    }
    private void shutdown() {
        synchronized(this) {if(stopping)return;stopping=true;}
        RuntimeState.phoneVPN(this,"stopping",lastError);
        // HEV espera su inicialización al parar. El proceso auxiliar limita esa
        // espera sin bloquear la interfaz ni detener el proceso del Gateway.
        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(this::finishProcess,2000);
        new Thread(()-> {
            if(device!=null) { stopTunnel(); try { device.close(); } catch(Exception ignored) {} }
            finishProcess();
        },"cerrar-vpn").start();
        active=false;worker.shutdown();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();
    }
    @Override public void onDestroy() {shutdown();super.onDestroy();}
}
