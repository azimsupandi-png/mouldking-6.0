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
 * Drives one to three Mould King Module 6.0 hubs by broadcasting their telegrams
 * as BLE advertisements (the hubs are not connected to; they only listen).
 *
 * Telegram layout (10 bytes): 0x61+module, 0x7B, 0xA7, six channel bytes
 * (0x80 = stop, above = forward, below = reverse), 0x9E-module.
 * With one hub the telegram is updated whenever the values change. With several
 * hubs the telegrams are broadcast in turn, one every ROTATE_MS.
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
    private static final long ROTATE_MS = 100;
    private static final long NEUTRAL_BEFORE_STOP_MS = 250;
    private static final int CHANNELS = 6;
    private static final int MAX_HUBS = 3;

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
    private int rotateIdx;
    private int[] modules = {0};
    private int[][] latest = new int[1][CHANNELS];

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
                if (failCount > 40) {
                    stopNow();
                    listener.onState("error");
                } else if (modules.length == 1) {
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
            if (modules.length > 1) {
                handler.removeCallbacks(rotateTask);
                handler.post(rotateTask);
            } else {
                pushModule(0);
            }
            listener.onState("ready");
        }
    };

    private final Runnable rotateTask = new Runnable() {
        @Override
        public void run() {
            if (!running || connecting) return;
            if (rotateIdx >= modules.length) rotateIdx = 0;
            pushModule(rotateIdx);
            rotateIdx = (rotateIdx + 1) % modules.length;
            handler.postDelayed(this, ROTATE_MS);
        }
    };

    private final Runnable pushTask = new Runnable() {
        @Override
        public void run() {
            pushScheduled = false;
            pushModule(0);
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

    /** modules: one to three distinct module numbers, each 0..2 (M1..M3). */
    void start(int[] mods) {
        if (running || starting) return;
        if (mods == null || mods.length < 1 || mods.length > MAX_HUBS) {
            listener.onState("error");
            return;
        }
        for (int i = 0; i < mods.length; i++) {
            if (mods[i] < 0 || mods[i] > 2) {
                listener.onState("error");
                return;
            }
            for (int j = 0; j < i; j++) {
                if (mods[i] == mods[j]) {
                    listener.onState("error");
                    return;
                }
            }
        }
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
        modules = mods.clone();
        latest = new int[modules.length][CHANNELS];
        rotateIdx = 0;
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

    /**
     * Remember the newest values (-100..100) and broadcast them. The array holds
     * six values per hub, in the order the hubs were passed to start().
     */
    void setFrame(int[] pct) {
        for (int k = 0; k < modules.length; k++) {
            for (int j = 0; j < CHANNELS; j++) {
                int idx = k * CHANNELS + j;
                latest[k][j] = idx < pct.length ? pct[idx] : 0;
            }
        }
        if (running && !connecting && set != null && modules.length == 1) schedulePush();
    }

    /** Broadcast neutral values, then stop advertising shortly after. */
    void stop() {
        if (!running && !starting) return;
        stopping = true;
        handler.removeCallbacks(finishConnect);
        handler.removeCallbacks(pushTask);
        pushScheduled = false;
        if (running && set != null) {
            for (int k = 0; k < modules.length; k++) {
                for (int j = 0; j < CHANNELS; j++) latest[k][j] = 0;
            }
            connecting = false;
            long wait;
            if (modules.length > 1) {
                handler.removeCallbacks(rotateTask);
                handler.post(rotateTask);
                wait = modules.length * ROTATE_MS * 2 + 150;
            } else {
                pushModule(0);
                wait = NEUTRAL_BEFORE_STOP_MS;
            }
            handler.postDelayed(stopTask, wait);
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
        handler.removeCallbacks(rotateTask);
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

    private void pushModule(int k) {
        if (!running || set == null || k >= modules.length) return;
        try {
            set.setAdvertisingData(dataFor(telegram(modules[k], latest[k])));
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
