package org.headscalegateway.upgradetest;

import android.app.Instrumentation;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.sqlite.SQLiteDatabase;
import android.os.Bundle;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;

/** Sonda firmada aparte: solo datos ficticios en una instalación release vacía. */
public final class UpgradeProbe extends Instrumentation {
    private String phase;
    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        phase = arguments.getString("phase", "verify");
        start();
    }
    private static String hash(byte[] value) throws Exception {
        StringBuilder out = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(value)) out.append(String.format("%02x", b & 255));
        return out.toString();
    }
    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            Context target = getTargetContext();
            int code = target.getPackageManager().getPackageInfo(target.getPackageName(), 0).versionCode;
            SharedPreferences probe = target.getSharedPreferences("upgrade_probe", Context.MODE_PRIVATE);
            File marker = new File(target.getNoBackupFilesDir(), "upgrade-probe.txt");
            File database = new File(target.getFilesDir(), "upgrade-probe.sqlite");
            java.lang.reflect.Method secret = target.getClassLoader().loadClass("org.headscalegateway.android.RuntimeState")
                .getDeclaredMethod("secret", Context.class, String.class);
            secret.setAccessible(true);
            if (phase.equals("seed")) {
                if (code != 10040074 || new File(target.getFilesDir(), "gateway/gateway.sqlite").exists() || marker.exists() || database.exists() || probe.contains("secret_hash"))
                    throw new IllegalStateException("Se requiere una instalación 1.4.7 de prueba vacía");
                String generated = (String) secret.invoke(null, target, "upgrade_probe_secret");
                probe.edit().putString("secret_hash", hash(generated.getBytes(StandardCharsets.UTF_8))).commit();
                Files.write(marker.toPath(), "Datos ficticios conservados desde 1.4.7".getBytes(StandardCharsets.UTF_8));
                try (SQLiteDatabase db = SQLiteDatabase.openOrCreateDatabase(database, null)) {
                    db.execSQL("CREATE TABLE fixture (value TEXT NOT NULL)");
                    db.execSQL("INSERT INTO fixture VALUES ('upgrade-1.4.7')");
                }
            } else {
                if (code != 10040075) throw new IllegalStateException("No está instalada la nueva revisión");
                String recovered = (String) secret.invoke(null, target, "upgrade_probe_secret");
                if (!hash(recovered.getBytes(StandardCharsets.UTF_8)).equals(probe.getString("secret_hash", "")))
                    throw new IllegalStateException("No se conserva el secreto de Android Keystore");
                if (!new String(Files.readAllBytes(marker.toPath()), StandardCharsets.UTF_8).equals("Datos ficticios conservados desde 1.4.7"))
                    throw new IllegalStateException("No se conserva el archivo privado");
                try (SQLiteDatabase db = SQLiteDatabase.openDatabase(database.getPath(), null, SQLiteDatabase.OPEN_READONLY);
                     android.database.Cursor cursor = db.rawQuery("SELECT value FROM fixture", null)) {
                    if (!cursor.moveToFirst() || !cursor.getString(0).equals("upgrade-1.4.7"))
                        throw new IllegalStateException("No se conserva SQLite");
                }
                result.putString("preserved", "private-file,SQLite,SharedPreferences,Android-Keystore-secret");
            }
            result.putString("phase", phase);
            result.putString("version_code", Integer.toString(code));
            result.putString("result", "OK");
            finish(-1, result);
        } catch (Throwable error) {
            result.putString("result", "FAILED: " + error.getClass().getSimpleName());
            finish(0, result);
        }
    }
}
