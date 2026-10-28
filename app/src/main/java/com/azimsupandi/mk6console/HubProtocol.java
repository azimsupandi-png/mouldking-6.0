package com.azimsupandi.mk6console;

/**
 * Telegram layouts for the Mould King hubs (pure functions, no Android classes).
 *
 * MK 6.0 (6 channels per hub): 10 bytes 0x61+module, 0x7B, 0xA7, six channel bytes
 * (0x80 = stop, above = forward, below = reverse), 0x9E-module. One telegram per hub.
 *
 * MK 4.0 (4 channels per hub): one shared 10-byte telegram 0x7D, 0x7B, 0xA7, six data
 * bytes, 0x82. The data bytes hold three hubs (M1..M3) with four channels each, one nibble
 * per channel: 0x8 = stop, 0x9..0xF = forward level 1..7, 0x1..0x7 = reverse level 1..7.
 *
 * Protocol credit: J0EK3R and pink0D (both MIT). See NOTICE.
 */
final class HubProtocol {

    static final int MK6 = 6;
    static final int MK4 = 4;
    /** Older MK 4.0 style hubs: byte-per-channel telegram as used by the MK 3.0 family (experimental). */
    static final int MK4_OLD = 3;

    static final byte[] CONNECT_MK6 = {
        0x6D, 0x7B, (byte) 0xA7, (byte) 0x80, (byte) 0x80, (byte) 0x80, (byte) 0x80, (byte) 0x92
    };
    static final byte[] CONNECT_MK4 = {
        (byte) 0xAD, 0x7B, (byte) 0xA7, (byte) 0x80, (byte) 0x80, (byte) 0x80, 0x4F, 0x52
    };

    static final byte[] CONNECT_OLD = {
        (byte) 0xAA, 0x7B, (byte) 0xA7, 0x00, 0x00, 0x00, 0x00, 0x55
    };

    private HubProtocol() {}

    static byte[] connectFor(int kind) {
        if (kind == MK4_OLD) return CONNECT_OLD;
        return kind == MK4 ? CONNECT_MK4 : CONNECT_MK6;
    }

    /** MK 6.0 telegram for one hub: moduleNo 0..2, pct holds six values -100..100. */
    static byte[] mk6(int moduleNo, int[] pct) {
        byte[] t = new byte[10];
        t[0] = (byte) (0x61 + moduleNo);
        t[1] = 0x7B;
        t[2] = (byte) 0xA7;
        for (int i = 0; i < 6; i++) t[3 + i] = (byte) channelByte(i < pct.length ? pct[i] : 0);
        t[9] = (byte) (0x9E - moduleNo);
        return t;
    }

    /** Older MK 4.0 hub: 0x66, 0x7B, 0xA7, four channel bytes (0x80 = stop), 0x99. */
    static byte[] mk4Old(int[] pct) {
        byte[] t = new byte[8];
        t[0] = 0x66;
        t[1] = 0x7B;
        t[2] = (byte) 0xA7;
        for (int i = 0; i < 4; i++) t[3 + i] = (byte) channelByte(i < pct.length ? pct[i] : 0);
        t[7] = (byte) 0x99;
        return t;
    }

    static int channelByte(float pct) {
        if (pct >= -1f && pct <= 1f) return 0x80;
        float a = Math.min(Math.abs(pct), 100f);
        float r = Math.min(0x80, a * 0x80 / 100f);
        if (pct < 0) return (int) Math.max(0, 0x80 - r);
        return (int) Math.min(0xFF, 0x80 + r);
    }

    /** One MK 4.0 channel as a nibble. */
    static int nibble(int pct) {
        if (pct >= -1 && pct <= 1) return 0x8;
        int mag = Math.round(Math.min(Math.abs(pct), 100) * 7f / 100f);
        if (mag <= 0) return 0x8;
        return pct > 0 ? 0x8 + mag : mag;
    }

    /**
     * Shared MK 4.0 telegram. kinds[k] / modules[k] describe slot k; only slots of kind MK4
     * are used. vals[k] holds that slot's channel values (at least four).
     */
    static byte[] mk4(int[] kinds, int[] modules, int[][] vals) {
        byte[] t = {
            0x7D, 0x7B, (byte) 0xA7, (byte) 0x88, (byte) 0x88, (byte) 0x88,
            (byte) 0x88, (byte) 0x88, (byte) 0x88, (byte) 0x82
        };
        for (int k = 0; k < kinds.length; k++) {
            if (kinds[k] != MK4 || modules[k] < 0 || modules[k] > 2) continue;
            for (int j = 0; j < 4; j++) {
                int v = j < vals[k].length ? vals[k][j] : 0;
                int idx = 3 + 2 * modules[k] + (j >> 1);
                int nib = nibble(v);
                if ((j & 1) == 0) t[idx] = (byte) ((t[idx] & 0x0F) | (nib << 4));
                else t[idx] = (byte) ((t[idx] & 0xF0) | nib);
            }
        }
        return t;
    }
}
