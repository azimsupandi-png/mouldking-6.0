package com.azimsupandi.mk6console;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.drawable.Icon;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.net.Uri;
import android.os.Build;
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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        BluetoothManager manager = (BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE);
        BluetoothAdapter adapter = manager != null ? manager.getAdapter() : null;
        mk6 = new Mk6Advertiser(adapter, this::notifyPage);

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
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        // The advertiser was stopped in onPause; make the page show that.
        if (!mk6.isActive() && pendingMods == null) notifyPage("stopped");
    }

    @Override
    protected void onDestroy() {
        mk6.destroy();
        super.onDestroy();
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
