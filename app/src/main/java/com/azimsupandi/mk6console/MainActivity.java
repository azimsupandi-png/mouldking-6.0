package com.azimsupandi.mk6console;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.BroadcastReceiver;
import android.content.ContentValues;
import android.content.Context;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.SystemClock;
import java.util.Locale;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.drawable.Icon;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.provider.Settings;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {

    private static final int REQ_BLUETOOTH = 41;
    private static final int REQ_EXPORT = 42;
    private static final int REQ_IMPORT = 43;
    private static final int MAX_IMPORT_BYTES = 1024 * 1024;
    private static final String PAGE = "file:///android_asset/index.html";

    private WebView web;
    private Mk6Advertiser mk6;
    private int[] pendingMods;
    private String pendingExport;
    private String pendingModel;
    private boolean pageReady;
    private Vibrator vibrator;
    private final BroadcastReceiver btReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (!BluetoothAdapter.ACTION_STATE_CHANGED.equals(intent.getAction())) return;
            int st = intent.getIntExtra(BluetoothAdapter.EXTRA_STATE, BluetoothAdapter.ERROR);
            if (st == BluetoothAdapter.STATE_ON) notifyApp("bt1");
            if (st == BluetoothAdapter.STATE_OFF || st == BluetoothAdapter.STATE_TURNING_OFF) notifyApp("bt0");
            if (st == BluetoothAdapter.STATE_TURNING_OFF || st == BluetoothAdapter.STATE_OFF) {
                boolean wasActive = mk6.isActive();
                mk6.destroy();
                if (wasActive) notifyApp("btoff");
            }
        }
    };
    private boolean btReceiverOn;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (Build.VERSION.SDK_INT >= 28) {
            // Draw into the camera cutout area too, so no black strip is left at the top.
            try {
                WindowManager.LayoutParams lp = getWindow().getAttributes();
                lp.layoutInDisplayCutoutMode = Build.VERSION.SDK_INT >= 30
                    ? WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
                    : WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
                getWindow().setAttributes(lp);
            } catch (RuntimeException ignored) { }
        }

        BluetoothManager manager = (BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE);
        BluetoothAdapter adapter = manager != null ? manager.getAdapter() : null;
        mk6 = new Mk6Advertiser(adapter, this::notifyPage);
        try {
            registerReceiver(btReceiver, new IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED));
            btReceiverOn = true;
        } catch (RuntimeException ignored) {
            btReceiverOn = false;
        }

        web = new WebView(this);
        setContentView(web);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        readModelExtra(getIntent());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !request.getUrl().toString().startsWith("file:///android_asset/");
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                pageReady = true;
                deliverModel();
            }
        });
        web.addJavascriptInterface(new Bridge(), "MK6Bridge");
        web.loadUrl(PAGE);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        readModelExtra(intent);
        deliverModel();
    }

    private void readModelExtra(Intent intent) {
        if (intent == null) return;
        String id = intent.getStringExtra("model");
        if (id != null && id.matches("[A-Za-z0-9_-]{1,40}")) pendingModel = id;
        intent.removeExtra("model");
    }

    private void deliverModel() {
        if (!pageReady || pendingModel == null || web == null) return;
        final String js = "window.openModel&&window.openModel(" + JSONObject.quote(pendingModel) + ")";
        pendingModel = null;
        web.post(() -> web.evaluateJavascript(js, null));
    }

    private void buzz(long[] pattern) {
        if (vibrator == null || !vibrator.hasVibrator()) return;
        try {
            vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1));
        } catch (RuntimeException ignored) {
            // Vibration is a nicety; never let it break control.
        }
    }

    private Intent modelIntent(String id) {
        Intent i = new Intent(this, MainActivity.class);
        i.setAction(Intent.ACTION_VIEW);
        i.putExtra("model", id);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return i;
    }

    private ShortcutInfo shortcutFor(String prefix, String id, String name) {
        String label = name == null || name.trim().isEmpty() ? "Model" : name.trim();
        return new ShortcutInfo.Builder(this, prefix + id)
            .setShortLabel(label.length() > 10 ? label.substring(0, 10) : label)
            .setLongLabel(label)
            .setIcon(Icon.createWithResource(this, R.mipmap.ic_launcher))
            .setIntent(modelIntent(id))
            .build();
    }

    @Override
    protected void onPause() {
        // Never leave motors running while the app is not on screen.
        mk6.stop();
        setTilt(false);
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        notifyApp("resume");
        // The advertiser was stopped in onPause; make the page show that.
        if (!mk6.isActive() && pendingMods == null) notifyPage("stopped");
    }

    @Override
    protected void onDestroy() {
        if (btReceiverOn) {
            try { unregisterReceiver(btReceiver); } catch (RuntimeException ignored) { }
            btReceiverOn = false;
        }
        setTilt(false);
        mk6.destroy();
        super.onDestroy();
    }

    private boolean fullScreen = true;

    private void applyFull() {
        int f = fullScreen
            ? (android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | android.view.View.SYSTEM_UI_FLAG_FULLSCREEN
                | android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY)
            : android.view.View.SYSTEM_UI_FLAG_VISIBLE;
        try { getWindow().getDecorView().setSystemUiVisibility(f); } catch (RuntimeException ignored) { }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) applyFull();
    }

    private SensorManager sm;
    private boolean tiltOn;
    private long lastTilt;
    private final SensorEventListener tiltL = new SensorEventListener() {
        @Override public void onSensorChanged(SensorEvent e) {
            long now = SystemClock.uptimeMillis();
            if (now - lastTilt < 30) return;
            lastTilt = now;
            int rot = 0;
            try { rot = getWindowManager().getDefaultDisplay().getRotation() * 90; } catch (RuntimeException ignored) { }
            final String js = String.format(Locale.US,
                "window.onTilt&&window.onTilt(%.2f,%.2f,%d)", e.values[0], e.values[1], rot);
            web.evaluateJavascript(js, null);
        }
        @Override public void onAccuracyChanged(Sensor s, int a) { }
    };

    private void setTilt(boolean on) {
        if (on == tiltOn) return;
        if (sm == null) sm = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        if (sm == null) { if (on) notifyApp("notilt"); return; }
        if (on) {
            Sensor a = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            if (a == null) { notifyApp("notilt"); return; }
            sm.registerListener(tiltL, a, SensorManager.SENSOR_DELAY_GAME);
            tiltOn = true;
        } else {
            sm.unregisterListener(tiltL);
            tiltOn = false;
        }
    }

    private void requestStart(int[] mods) {
        if (Build.VERSION.SDK_INT >= 31
                && checkSelfPermission(Manifest.permission.BLUETOOTH_ADVERTISE)
                    != PackageManager.PERMISSION_GRANTED) {
            pendingMods = mods;
            requestPermissions(new String[] {Manifest.permission.BLUETOOTH_ADVERTISE}, REQ_BLUETOOTH);
            return;
        }
        mk6.start(mods);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQ_BLUETOOTH) return;
        boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
        if (granted && pendingMods != null) {
            mk6.start(pendingMods);
        } else {
            notifyPage("denied");
        }
        pendingMods = null;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_EXPORT && requestCode != REQ_IMPORT) return;
        String kind = requestCode == REQ_EXPORT ? "export" : "import";
        if (resultCode != RESULT_OK || data == null || data.getData() == null) {
            pendingExport = null;
            notifyFile(kind, "cancel");
            return;
        }
        Uri uri = data.getData();
        try {
            if (requestCode == REQ_EXPORT) {
                String text = pendingExport == null ? "" : pendingExport;
                pendingExport = null;
                try (OutputStream out = getContentResolver().openOutputStream(uri, "wt")) {
                    if (out == null) throw new java.io.IOException("no stream");
                    out.write(text.getBytes(StandardCharsets.UTF_8));
                }
                notifyFile("export", "ok");
            } else {
                String text = readLimited(uri);
                if (text == null) {
                    notifyFile("import", "fail");
                    return;
                }
                final String js = "window.onImportText&&window.onImportText(" + JSONObject.quote(text) + ")";
                web.post(() -> web.evaluateJavascript(js, null));
            }
        } catch (Exception e) {
            notifyFile(kind, "fail");
        }
    }

    /** Saves the models as Downloads/MK6-Console-backup.json (needs no permission on Android 10 and up). */
    private boolean writeBackup(String text) {
        if (text == null || Build.VERSION.SDK_INT < 29) return false;
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        if (bytes.length == 0 || bytes.length > MAX_IMPORT_BYTES) return false;
        try {
            android.content.ContentResolver cr = getContentResolver();
            Uri coll = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
            String name = "MK6-Console-backup.json";
            try {
                cr.delete(coll,
                    MediaStore.MediaColumns.DISPLAY_NAME + "=? AND " + MediaStore.MediaColumns.RELATIVE_PATH + "=?",
                    new String[] {name, Environment.DIRECTORY_DOWNLOADS + "/"});
            } catch (RuntimeException ignored) {
                // A copy from an earlier install cannot be replaced; a new one is added next to it.
            }
            ContentValues v = new ContentValues();
            v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
            v.put(MediaStore.MediaColumns.MIME_TYPE, "application/json");
            v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
            Uri u = cr.insert(coll, v);
            if (u == null) return false;
            try (OutputStream out = cr.openOutputStream(u, "wt")) {
                if (out == null) return false;
                out.write(bytes);
            }
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private String readLimited(Uri uri) throws java.io.IOException {
        try (InputStream in = getContentResolver().openInputStream(uri)) {
            if (in == null) return null;
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] chunk = new byte[8192];
            int n;
            while ((n = in.read(chunk)) > 0) {
                buf.write(chunk, 0, n);
                if (buf.size() > MAX_IMPORT_BYTES) return null;
            }
            return new String(buf.toByteArray(), StandardCharsets.UTF_8);
        }
    }

    private void notifyPage(final String state) {
        if (web == null) return;
        web.post(() -> web.evaluateJavascript(
            "window.onHubState&&window.onHubState('" + state + "')", null));
    }

    private void notifyApp(final String event) {
        if (web == null) return;
        web.post(() -> web.evaluateJavascript(
            "window.onAppEvent&&window.onAppEvent('" + event + "')", null));
    }

    private void notifyFile(final String kind, final String result) {
        if (web == null) return;
        web.post(() -> web.evaluateJavascript(
            "window.onFileResult&&window.onFileResult('" + kind + "','" + result + "')", null));
    }

    private static int[] parseMods(String csv) {
        if (csv == null) return null;
        String[] parts = csv.split(",");
        if (parts.length < 1 || parts.length > 3) return null;
        int[] out = new int[parts.length];
        try {
            for (int i = 0; i < parts.length; i++) out[i] = Integer.parseInt(parts[i].trim());
        } catch (NumberFormatException e) {
            return null;
        }
        return out;
    }

    private static int[] parseFrame(String csv) {
        if (csv == null) return null;
        String[] parts = csv.split(",");
        if (parts.length != 6 && parts.length != 12 && parts.length != 18) return null;
        int[] out = new int[parts.length];
        try {
            for (int i = 0; i < parts.length; i++) {
                out[i] = Math.max(-100, Math.min(100, Integer.parseInt(parts[i].trim())));
            }
        } catch (NumberFormatException e) {
            return null;
        }
        return out;
    }

    /** Methods the page can call; they run on a WebView thread, so hop to the UI thread. */
    private final class Bridge {
        @JavascriptInterface
        public boolean btOn() {
            try {
                BluetoothManager bm = (BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE);
                BluetoothAdapter ad = bm != null ? bm.getAdapter() : null;
                return ad != null && ad.isEnabled();
            } catch (RuntimeException e) {
                return false;
            }
        }

        @JavascriptInterface
        public void btSettings() {
            runOnUiThread(() -> {
                try {
                    startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS));
                } catch (RuntimeException ignored) {
                }
            });
        }

        @JavascriptInterface
        public void immersive(final boolean on) {
            runOnUiThread(() -> { fullScreen = on; applyFull(); });
        }

        @JavascriptInterface
        public void tilt(final boolean on) {
            runOnUiThread(() -> setTilt(on));
        }

        @JavascriptInterface
        public void start(final String mods) {
            final int[] parsed = parseMods(mods);
            runOnUiThread(() -> {
                if (parsed == null) {
                    notifyPage("error");
                } else {
                    requestStart(parsed);
                }
            });
        }

        @JavascriptInterface
        public int battery() {
            try {
                Intent b = registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
                if (b == null) return -1;
                int level = b.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                int scale = b.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
                if (level < 0 || scale <= 0) return -1;
                return Math.round(level * 100f / scale);
            } catch (RuntimeException e) {
                return -1;
            }
        }

        @JavascriptInterface
        public void autoBackup(final String json) {
            new Thread(() -> notifyApp(writeBackup(json) ? "backupok" : "backupfail")).start();
        }

        @JavascriptInterface
        public void stop() {
            runOnUiThread(() -> mk6.stop());
        }

        @JavascriptInterface
        public void send(String csv) {
            final int[] frame = parseFrame(csv);
            if (frame == null) return;
            runOnUiThread(() -> mk6.setFrame(frame));
        }

        @JavascriptInterface
        public void haptic(final String kind) {
            long[] p;
            if ("estop".equals(kind)) p = new long[] {0, 90, 70, 90};
            else if ("warn".equals(kind)) p = new long[] {0, 200, 100, 200, 100, 200};
            else if ("lost".equals(kind)) p = new long[] {0, 300};
            else if ("ok".equals(kind)) p = new long[] {0, 40};
            else p = new long[] {0, 15};
            final long[] pattern = p;
            runOnUiThread(() -> buzz(pattern));
        }

        @JavascriptInterface
        public void pinModel(final String id, final String name) {
            runOnUiThread(() -> {
                try {
                    ShortcutManager sm = getSystemService(ShortcutManager.class);
                    if (sm != null && sm.isRequestPinShortcutSupported()
                            && id != null && id.matches("[A-Za-z0-9_-]{1,40}")) {
                        sm.requestPinShortcut(shortcutFor("pin_", id, name), null);
                    } else {
                        notifyApp("nopin");
                    }
                } catch (RuntimeException e) {
                    notifyApp("nopin");
                }
            });
        }

        @JavascriptInterface
        public void shortcuts(final String json) {
            runOnUiThread(() -> {
                try {
                    ShortcutManager sm = getSystemService(ShortcutManager.class);
                    if (sm == null) return;
                    JSONArray arr = new JSONArray(json);
                    List<ShortcutInfo> list = new ArrayList<>();
                    int max = Math.min(arr.length(), Math.min(4, sm.getMaxShortcutCountPerActivity()));
                    for (int i = 0; i < max; i++) {
                        JSONObject o = arr.getJSONObject(i);
                        String id = o.optString("id", "");
                        if (!id.matches("[A-Za-z0-9_-]{1,40}")) continue;
                        list.add(shortcutFor("dyn_", id, o.optString("name", "")));
                    }
                    sm.setDynamicShortcuts(list);
                } catch (Exception ignored) {
                    // Shortcuts are optional.
                }
            });
        }

        @JavascriptInterface
        public void exportFile(final String name, final String text) {
            runOnUiThread(() -> {
                pendingExport = text;
                Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("application/json");
                intent.putExtra(Intent.EXTRA_TITLE, name);
                try {
                    startActivityForResult(intent, REQ_EXPORT);
                } catch (RuntimeException e) {
                    pendingExport = null;
                    notifyFile("export", "fail");
                }
            });
        }

        @JavascriptInterface
        public void importFile() {
            runOnUiThread(() -> {
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                try {
                    startActivityForResult(intent, REQ_IMPORT);
                } catch (RuntimeException e) {
                    notifyFile("import", "fail");
                }
            });
        }
    }
}
