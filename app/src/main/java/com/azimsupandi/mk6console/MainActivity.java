package com.azimsupandi.mk6console;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {

    private static final int REQ_BLUETOOTH = 41;
    private static final String PAGE = "file:///android_asset/index.html";

    private WebView web;
    private Mk6Advertiser mk6;
    private int pendingModule = -1;

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
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !request.getUrl().toString().startsWith("file:///android_asset/");
            }
        });
        web.addJavascriptInterface(new Bridge(), "MK6Bridge");
        web.loadUrl(PAGE);
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
        if (!mk6.isActive() && pendingModule < 0) notifyPage("stopped");
    }

    @Override
    protected void onDestroy() {
        mk6.destroy();
        super.onDestroy();
    }

    private void requestStart(int module) {
        if (Build.VERSION.SDK_INT >= 31
                && checkSelfPermission(Manifest.permission.BLUETOOTH_ADVERTISE)
                    != PackageManager.PERMISSION_GRANTED) {
            pendingModule = module;
            requestPermissions(new String[] {Manifest.permission.BLUETOOTH_ADVERTISE}, REQ_BLUETOOTH);
            return;
        }
        mk6.start(module);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQ_BLUETOOTH) return;
        boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
        if (granted && pendingModule >= 0) {
            mk6.start(pendingModule);
        } else {
            notifyPage("denied");
        }
        pendingModule = -1;
    }

    private void notifyPage(final String state) {
        if (web == null) return;
        web.post(() -> web.evaluateJavascript(
            "window.onHubState&&window.onHubState('" + state + "')", null));
    }

    private static int[] parseFrame(String csv) {
        if (csv == null) return null;
        String[] parts = csv.split(",");
        if (parts.length != 6) return null;
        int[] out = new int[6];
        try {
            for (int i = 0; i < 6; i++) {
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
        public void start(final int module) {
            runOnUiThread(() -> requestStart(module));
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
    }
}
