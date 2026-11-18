package org.headscalegateway.android;

import android.webkit.WebView;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicReference;

/** Autorización y revocación del puente; nunca utiliza datos de la APK habitual. */
final class BridgeSecurityChecks {
    private final SmokeInstrumentation s;
    BridgeSecurityChecks(SmokeInstrumentation s){this.s=s;}
    private void require(boolean ok,String message){if(!ok)throw new AssertionError(message);}
    void run()throws Exception {
        require(s.context.getPackageName().endsWith(".lab"),"Solo laboratorio");
        AtomicReference<PanelDownloads> reference=new AtomicReference<>();
        s.runOnMainSync(()->reference.set(new PanelDownloads(s.activity,(WebView)s.activity.findViewById(R.id.panel_webview))));
        PanelDownloads bridge=reference.get();
        try {
            String base=RuntimeState.base(s.context);
            bridge.trust(base+"/admin/");String capability=bridge.capability();
            require(!capability.isEmpty(),"No se autoriza el documento local");
            for(String forged:new String[]{"",base,"https://example.test",capability+"x"})
                require(bridge.beginBlob(forged,"prueba.txt","text/plain").isEmpty(),"Un origen declarado autoriza una descarga");
            require(s.browser("DescargasGateway.beginBlob(location.origin,'intruso.txt','text/plain')").equals("\"\""),"El puente real acepta un origen como credencial");
            String transfer=bridge.beginBlob(capability,"prueba.txt","text/plain");
            require(!transfer.isEmpty(),"Se rechazó la capacidad vigente");
            bridge.append(transfer,"cHJ1ZWJh");
            bridge.trust(null);
            require(bridge.beginBlob(capability,"prueba.txt","text/plain").isEmpty(),"La navegación no revoca la capacidad");
            boolean rejected=false;
            try {bridge.append(transfer,"cHJ1ZWJh");}catch(IOException expected){rejected=true;}
            require(rejected,"La transferencia anterior sigue autorizada");
            bridge.trust(base+"/admin/");
            require(!capability.equals(bridge.capability()),"Se reutiliza la capacidad de otro documento");
            require(bridge.beginBlob(capability,"prueba.txt","text/plain").isEmpty(),"Se acepta una capacidad caducada");
            bridge.trust("https://example.test/admin/");
            require(bridge.capability().isEmpty(),"Un documento externo obtiene autorización");
        } finally {bridge.detach();}
        new FunctionalChecks(s).bridgeExports();
        require(s.browser("typeof androidDocumentCapability==='undefined' && !Object.keys(window).some(k=>/capability/i.test(k))").equals("true"),"Se expone la capacidad en window");
    }
}
