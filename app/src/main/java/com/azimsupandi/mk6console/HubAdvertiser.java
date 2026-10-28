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
 * Drives one to three Mould King hubs (Module 6.0 and/or 4.0) by broadcasting their
 * telegrams as BLE advertisements (the hubs are not connected to; they only listen).
 *
 * See HubProtocol for the telegram layouts. A "unit" is one advertisement: every MK 6.0 hub
 * has its own unit, and all MK 4.0 hubs share a single unit. With one unit the telegram is
 * updated whenever the values change. With several units they are broadcast in turn,
 * one every ROTATE_MS.
 * Protocol credit: J0EK3R and pink0D (MIT). See NOTICE.
 *
 * All methods must be called on the main thread.
 */
final class HubAdvertiser {

    interface Listener {
        void onState(String state);
    }

    private static final byte[] ADDR = {
        (byte) 0xC1, (byte) 0xC2, (byte) 0xC3, (byte) 0xC4, (byte) 0xC5
    };
    private static final int CTX = 0x25;
    private static final int COMPANY_ID = 0xFFF0;
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
    private int connectIdx;
    private int[] kinds = {HubProtocol.MK6};
    private int[] modules = {0};
    private int[] unitKind = {HubProtocol.MK6};
    private int[] unitSlot = {0};
    private int[] connectKinds = {HubProtocol.MK6};
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
                    connectIdx = 0;
                    if (connectKinds.length > 1) {
                        handler.postDelayed(connectRotateTask, ROTATE_MS);
                    }
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
                } else if (unitKind.length == 1) {
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
            handler.removeCallbacks(connectRotateTask);
            if (unitKind.length > 1) {
                handler.removeCallbacks(rotateTask);
                handler.post(rotateTask);
            } else {
                pushUnit(0);
            }
            listener.onState("ready");
        }
    };

    /** While connecting with mixed hub types, alternate the connect telegrams. */
    private final Runnable connectRotateTask = new Runnable() {
        @Override
        public void run() {
            if (!running || !connecting || set == null) return;
            connectIdx = (connectIdx + 1) % connectKinds.length;
            try {
                set.setAdvertisingData(dataFor(HubProtocol.connectFor(connectKinds[connectIdx])));
            } catch (RuntimeException e) {
                stopNow();
                listener.onState("error");
                return;
            }
            handler.postDelayed(this, ROTATE_MS);
        }
    };

    private final Runnable rotateTask = new Runnable() {
        @Override
        public void run() {
            if (!running || connecting) return;
            if (rotateIdx >= unitKind.length) rotateIdx = 0;
            pushUnit(rotateIdx);
            rotateIdx = (rotateIdx + 1) % unitKind.length;
            handler.postDelayed(this, ROTATE_MS);
        }
    };

    private final Runnable pushTask = new Runnable() {
        @Override
        public void run() {
            pushScheduled = false;
            pushUnit(0);
        }
    };

    private final Runnable stopTask = new Runnable() {
        @Override
        public void run() {
            stopNow();
        }
    };

    HubAdvertiser(BluetoothAdapter adapter, Listener listener) {
        this.adapter = adapter;
        this.listener = listener;
    }

    boolean isActive() {
        return running || starting;
    }

    /**
     * kinds: HubProtocol.MK6 or MK4 for each hub; mods: its module number 0..2 (M1..M3).
     * One to three hubs. Module numbers must be distinct among hubs of the same kind.
     */
    void start(int[] kindsIn, int[] mods) {
        if (running || starting) return;
        if (kindsIn == null || mods == null || kindsIn.length != mods.length
                || mods.length < 1 || mods.length > MAX_HUBS) {
            listener.onState("error");
            return;
        }
        for (int i = 0; i < mods.length; i++) {
            if (mods[i] < 0 || mods[i] > 2
                    || (kindsIn[i] != HubProtocol.MK6 && kindsIn[i] != HubProtocol.MK4
                        && kindsIn[i] != HubProtocol.MK4_OLD)) {
                listener.onState("error");
                return;
            }
            for (int j = 0; j < i; j++) {
                if (mods[i] == mods[j] && kindsIn[i] == kindsIn[j]) {
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
        kinds = kindsIn.clone();
        modules = mods.clone();
        latest = new int[modules.length][CHANNELS];
        buildUnits();
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
            advertiser.startAdvertisingSet(
                params, dataFor(HubProtocol.connectFor(connectKinds[0])), null, null, null, callback);
        } catch (SecurityException e) {
            starting = false;
            listener.onState("denied");
        } catch (RuntimeException e) {
            starting = false;
            listener.onState("error");
        }
    }

    /** Work out which advertisements are needed: one per MK 6.0 hub, one shared for all MK 4.0 hubs. */
    private void buildUnits() {
        int[] uk = new int[MAX_HUBS];
        int[] us = new int[MAX_HUBS];
        int n = 0;
        boolean has4 = false;
        boolean has6 = false;
        boolean hasOld = false;
        for (int k = 0; k < kinds.length; k++) {
            if (kinds[k] == HubProtocol.MK4) {
                if (!has4) {
                    has4 = true;
                    uk[n] = HubProtocol.MK4;
                    us[n] = k;
                    n++;
                }
            } else {
                if (kinds[k] == HubProtocol.MK4_OLD) hasOld = true; else has6 = true;
                uk[n] = kinds[k];
                us[n] = k;
                n++;
            }
        }
        unitKind = java.util.Arrays.copyOf(uk, n);
        unitSlot = java.util.Arrays.copyOf(us, n);
        int[] ck = new int[3];
        int c = 0;
        if (has6) ck[c++] = HubProtocol.MK6;
        if (has4) ck[c++] = HubProtocol.MK4;
        if (hasOld) ck[c++] = HubProtocol.MK4_OLD;
        connectKinds = java.util.Arrays.copyOf(ck, c);
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
        if (running && !connecting && set != null && unitKind.length == 1) schedulePush();
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
            handler.removeCallbacks(connectRotateTask);
            long wait;
            if (unitKind.length > 1) {
                handler.removeCallbacks(rotateTask);
                handler.post(rotateTask);
                wait = unitKind.length * ROTATE_MS * 2 + 150;
            } else {
                pushUnit(0);
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
        handler.removeCallbacks(connectRotateTask);
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

    private void pushUnit(int u) {
        if (!running || set == null || u >= unitKind.length) return;
        try {
            byte[] t;
            if (unitKind[u] == HubProtocol.MK4) t = HubProtocol.mk4(kinds, modules, latest);
            else if (unitKind[u] == HubProtocol.MK4_OLD) t = HubProtocol.mk4Old(latest[unitSlot[u]]);
            else t = HubProtocol.mk6(modules[unitSlot[u]], latest[unitSlot[u]]);
            set.setAdvertisingData(dataFor(t));
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
}
