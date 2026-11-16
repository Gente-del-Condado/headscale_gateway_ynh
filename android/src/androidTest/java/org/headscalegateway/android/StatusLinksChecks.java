package org.headscalegateway.android;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.view.View;
import org.json.JSONObject;
import org.json.JSONTokener;
import java.util.concurrent.atomic.AtomicReference;

/** Toca el panel real, exclusivamente en .lab y con destinos ficticios interceptados. */
final class StatusLinksChecks {
    private final SmokeInstrumentation s;
    StatusLinksChecks(SmokeInstrumentation instrumentation){s=instrumentation;}
    private void require(boolean ok,String message){if(!ok)throw new AssertionError(message);}
    private void waitJS(String script,String message)throws Exception {
        long end=System.currentTimeMillis()+20000;
        while(System.currentTimeMillis()<end){if(s.browser(script).equals("true"))return;Thread.sleep(150);}
        throw new AssertionError(message);
    }
    private void tap(String key)throws Exception {
        String selector="a[data-status-key="+key+"]";
        // El sondeo periódico puede repintar el estado. La proyección ficticia y
        // la medida se hacen juntas, sin modificar la configuración persistente.
        String raw=s.browser("JSON.stringify((()=>{renderStatus(window.__statusLinksFixture);const link=document.querySelector("+JSONObject.quote(selector)+");if(!link)return {missing:true};link.scrollIntoView({block:'center',behavior:'instant'});const r=link.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,width:innerWidth}})())");
        Object value=new JSONTokener(raw).nextValue();
        require(value instanceof String,"No se pudo medir el enlace: "+key);
        JSONObject box=new JSONObject((String)value);
        require(!box.optBoolean("missing"),"El refresco retiró el enlace de laboratorio: "+key);
        int[] origin=new int[2],width=new int[1];
        s.runOnMainSync(()->{View web=s.activity.findViewById(R.id.panel_webview);web.getLocationOnScreen(origin);width[0]=web.getWidth();});
        float scale=width[0]/(float)box.getDouble("width"),x=origin[0]+(float)box.getDouble("x")*scale,y=origin[1]+(float)box.getDouble("y")*scale;
        android.graphics.Bitmap screenshot=s.getUiAutomation().takeScreenshot();
        if(screenshot!=null){try(java.io.FileOutputStream file=new java.io.FileOutputStream(new java.io.File(s.context.getExternalFilesDir(null),"status-links-"+key+".png"))){screenshot.compress(android.graphics.Bitmap.CompressFormat.PNG,100,file);}finally{screenshot.recycle();}}
        s.phase(new JSONObject().put("phase","statuslinks").put("detail","coordenadas "+key).put("x",x).put("y",y));
        s.browser("window.__statusLinksClick=false;document.querySelector("+JSONObject.quote(selector)+").addEventListener('click',event=>{window.__statusLinksClick=event.isTrusted},{once:true})");
        // Algunas ROM rechazan injectInputEvent de UiAutomation. El comando
        // shell entrega el toque al mismo control medido, solo en la APK .lab.
        try(android.os.ParcelFileDescriptor fd=s.getUiAutomation().executeShellCommand("input tap "+Math.round(x)+" "+Math.round(y));
            java.io.InputStream input=new android.os.ParcelFileDescriptor.AutoCloseInputStream(fd)) {
            byte[] bytes=new byte[1024];while(input.read(bytes)!=-1){}
        }
    }
    void run()throws Exception {
        require(s.context.getPackageName().endsWith(".lab"),"Solo se permite el paquete de laboratorio");
        s.runOnMainSync(()->s.activity.findViewById(R.id.nav_panel).performClick());
        waitJS("!!(document.getElementById('app')&&!document.getElementById('app').hidden&&window.gatewayAndroidOpenSection)","El panel no abrió su sesión normal");
        AtomicReference<String> opened=new AtomicReference<>("");
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(){
            @Override public Instrumentation.ActivityResult onStartActivity(Intent intent){
                if(Intent.ACTION_VIEW.equals(intent.getAction()) && intent.getData()!=null){
                    opened.set(intent.getData().toString());
                    return new Instrumentation.ActivityResult(Activity.RESULT_CANCELED,null);
                }
                return null;
            }
        };
        s.addMonitor(monitor);
        try {
            // Solo se sustituye la representación DOM; SQLite y tsnet no cambian.
            String fixture="{domain:'tablet-lab.example.test',headscale_url:'http://192.0.2.1:8080/',admin_domain_url:'https://admin.tablet-lab.example.test/admin/'}";
            s.browser("window.gatewayAndroidOpenSection('overview');window.__statusLinksFixture="+fixture+";window.__statusLinksOriginal=renderStatus;window.renderStatus=()=>window.__statusLinksOriginal(window.__statusLinksFixture);renderStatus(window.__statusLinksFixture)");
            require(s.browser("document.querySelector('#status dt').textContent==='Dominio principal'&&document.querySelector('a[data-status-key=domain]').href==='https://tablet-lab.example.test/'").equals("true"),"No se destaca el dominio principal");
            require(s.browser("document.documentElement.scrollWidth<=innerWidth+2").equals("true"),"Los enlaces desbordan el panel");
            for(String key:new String[]{"domain","headscale_url"}){
                String expected=key.equals("domain")?"https://tablet-lab.example.test/":"http://192.0.2.1:8080/";
                s.phase(new JSONObject().put("phase","statuslinks").put("detail","toque "+key));
                opened.set("");tap(key);
                long end=System.currentTimeMillis()+7000;
                while(opened.get().isEmpty()&&System.currentTimeMillis()<end)Thread.sleep(100);
                require(opened.get().equals(expected),"No se envió el enlace al navegador: "+key+"; destino="+opened.get()+"; toque="+s.browser("window.__statusLinksClick"));
                require(s.browser("location.pathname==='/admin/'").equals("true"),"Se abandonó el panel privado");
            }
            require(s.browser("(()=>{const link=document.querySelector('a[data-status-key=domain]');link.focus();const y=scrollY;renderStatus(window.__statusLinksFixture);return document.activeElement.dataset.statusKey==='domain'&&scrollY===y})()").equals("true"),"El refresco pierde el foco o desplaza el panel");
        } finally {
            s.removeMonitor(monitor);
            s.browser("window.renderStatus=window.__statusLinksOriginal;renderStatus("+s.api("GET","/api/v1/status",null).toString()+");delete window.__statusLinksFixture;delete window.__statusLinksOriginal");
        }
    }
}
