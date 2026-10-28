package com.azimsupandi.mk6console;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.le.AdvertiseData;
import android.bluetooth.le.AdvertisingSet;
import android.bluetooth.le.AdvertisingSetCallback;
import android.bluetooth.le.AdvertisingSetParameters;
import android.bluetooth.le.BluetoothLeAdvertiser;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;

/**
 * Drives a Mould King Module 6.0 hub by broadcasting its telegrams as BLE
 * advertisements (the hub is not connected to; it only listens).
 *
 * Telegram layout (10 bytes): 0x61+module, 0x7B, 0xA7, six channel bytes
 * (0x80 = stop, above = forward, below = reverse), 0x9E-module.
 * Protocol credit: J0EK3R (MIT). See NOTICE.
 *
 * All methods must be called on the main thread.
 */
final class Mk6Advertiser {

    interface Listener {
        void onState(String state);
    }

    private static final byte[] ADDR = {
        (byte) 0xC1, (byte) 0xC2, (byte) 0xC3, (byte) 0xC4, (byte) 0xC5
    };
    private static final int CTX = 0x25;
    private static final int COMPANY_ID = 0xFFF0;
    private static final byte[] CONNECT = {
        0x6D, 0x7B, (byte) 0xA7, (byte) 0x80, (byte) 0x80, (byte) 0x80, (byte) 0x80, (byte) 0x92
    };
    private static final long CONNECT_MS = 3000;
    private static final long MIN_GAP_MS = 60;
    private static final long NEUTRAL_BEFORE_STOP_MS = 250;
    private static final int CHANNELS = 6;

    private final BluetoothAdapter adapter;
    private final Listener listener;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private BluetoothLeAdvertiser advertiser;
    private AdvertisingSet set;
    private boolean starting;
    private boolean running;
    private boolean connecting;
    private boolean pushScheduled;
    private boolean stopping;
    private long lastPushAt;
    private int failCount;
    private int module;
    private final int[] latest = new int[CHANNELS];

    private final AdvertisingSetCallback callback = new AdvertisingSetCallback() {
        @Override
        public void onAdvertisingSetStarted(AdvertisingSet advertisingSet, int txPower, int status) {
            handler.post(() -> {
                starting = false;
                if (status == AdvertisingSetCallback.ADVERTISE_SUCCESS && !stopping) {
                    set = advertisingSet;
                    running = true;
                    connecting = true;
                    listener.onState("connecting");
                    handler.postDelayed(finishConnect, CONNECT_MS);
                } else if (status == AdvertisingSetCallback.ADVERTISE_SUCCESS) {
                    set = advertisingSet;
                    running = true;
                    stopNow();
                } else {
                    running = false;
                    listener.onState("error");
                }
            });
        }

        @Override
        public void onAdvertisingDataSet(AdvertisingSet advertisingSet, int status) {
            handler.post(() -> {
                if (status == AdvertisingSetCallback.ADVERTISE_SUCCESS) {
                    failCount = 0;
                    return;
                }
                if (!running || connecting || stopping) return;
                failCount++;
                if (failCount > 20) {
                    stopNow();
                    listener.onState("error");
                } else {
                    schedulePush();
                }
            });
        }

        @Override
        public void onAdvertisingSetStopped(AdvertisingSet advertisingSet) {
            handler.post(() -> {
                set = null;
                running = false;
                starting = false;
            });
        }
    };

    private final Runnable finishConnect = new Runnable() {
        @Override
        public void run() {
            if (!running) return;
            connecting = false;
            pushNow();
            listener.onState("ready");
        }
    };

    private final Runnable pushTask = new Runnable() {
        @Override
        public void run() {
            pushScheduled = false;
            pushNow();
        }
    };

    private final Runnable stopTask = new Runnable() {
        @Override
        public void run() {
            stopNow();
        }
    };

    Mk6Advertiser(BluetoothAdapter adapter, Listener listener) {
        this.adapter = adapter;
        this.listener = listener;
    }

    boolean isActive() {
        return running || starting;
    }

    void start(int moduleNo) {
        if (running || starting) return;
        if (adapter == null) {
            listener.onState("unsupported");
            return;
        }
        if (!adapter.isEnabled()) {
            listener.onState("off");
            return;
        }
        advertiser = adapter.getBluetoothLeAdvertiser();
        if (advertiser == null) {
            listener.onState("unsupported");
            return;
        }
        module = Math.max(0, Math.min(2, moduleNo));
        for (int i = 0; i < CHANNELS; i++) latest[i] = 0;
        failCount = 0;
        stopping = false;
        starting = true;
        try {
            AdvertisingSetParameters params = new AdvertisingSetParameters.Builder()
                .setLegacyMode(true)
                .setConnectable(true)
                .setScannable(true)
                .setInterval(AdvertisingSetParameters.INTERVAL_LOW)
                .setTxPowerLevel(AdvertisingSetParameters.TX_POWER_HIGH)
                .build();
            advertiser.startAdvertisingSet(params, dataFor(CONNECT), null, null, null, callback);
        } catch (SecurityException e) {
            starting = false;
            listener.onState("denied");
        } catch (RuntimeException e) {
            starting = false;
            listener.onState("error");
        }
    }

    /** Remember the newest values (-100..100 per channel) and broadcast them. */
    void setFrame(int[] pct) {
        for (int i = 0; i < CHANNELS && i < pct.length; i++) latest[i] = pct[i];
        if (running && !connecting && set != null) schedulePush();
    }

    /** Broadcast neutral values, then stop advertising shortly after. */
    void stop() {
        if (!running && !starting) return;
        stopping = true;
        handler.removeCallbacks(finishConnect);
        handler.removeCallbacks(pushTask);
        pushScheduled = false;
        if (running && set != null) {
            for (int i = 0; i < CHANNELS; i++) latest[i] = 0;
            connecting = false;
            pushNow();
            handler.postDelayed(stopTask, NEUTRAL_BEFORE_STOP_MS);
        } else if (!starting) {
            stopNow();
        }
    }

    void destroy() {
        handler.removeCallbacksAndMessages(null);
        stopNow();
    }

    private void stopNow() {
        handler.removeCallbacks(stopTask);
        handler.removeCallbacks(finishConnect);
        handler.removeCallbacks(pushTask);
        pushScheduled = false;
        connecting = false;
        try {
            if (advertiser != null && (running || starting)) {
                advertiser.stopAdvertisingSet(callback);
            }
        } catch (RuntimeException ignored) {
            // Bluetooth may have been switched off already.
        }
        set = null;
        running = false;
        starting = false;
        stopping = false;
        listener.onState("stopped");
    }

    private void schedulePush() {
        if (pushScheduled) return;
        long wait = Math.max(0, lastPushAt + MIN_GAP_MS - SystemClock.uptimeMillis());
        pushScheduled = true;
        handler.postDelayed(pushTask, wait);
    }

    private void pushNow() {
        if (!running || set == null) return;
        try {
            set.setAdvertisingData(dataFor(telegram(module, latest)));
            lastPushAt = SystemClock.uptimeMillis();
        } catch (RuntimeException e) {
            // Never keep broadcasting a stale command if the update could not be applied.
            stopNow();
            listener.onState("error");
        }
    }

    private static AdvertiseData dataFor(byte[] telegram) {
        byte[] payload = Mk6Crypt.rfPayload(ADDR, telegram, CTX);
        return new AdvertiseData.Builder()
            .setIncludeDeviceName(false)
            .setIncludeTxPowerLevel(false)
            .addManufacturerData(COMPANY_ID, payload)
            .build();
    }

    static byte[] telegram(int moduleNo, int[] pct) {
        byte[] t = new byte[10];
        t[0] = (byte) (0x61 + moduleNo);
        t[1] = 0x7B;
        t[2] = (byte) 0xA7;
        for (int i = 0; i < CHANNELS; i++) t[3 + i] = (byte) channelByte(pct[i]);
        t[9] = (byte) (0x9E - moduleNo);
        return t;
    }

    static int channelByte(float pct) {
        if (pct >= -1f && pct <= 1f) return 0x80;
        float a = Math.min(Math.abs(pct), 100f);
        float r = Math.min(0x80, a * 0x80 / 100f);
        if (pct < 0) return (int) Math.max(0, 0x80 - r);
        return (int) Math.min(0xFF, 0x80 + r);
    }
}
