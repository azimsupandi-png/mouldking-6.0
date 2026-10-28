package com.azimsupandi.mk6console;

/**
 * Packet encoder for the Mould King Module 6.0 advertising protocol.
 *
 * Port of get_rf_payload() from CryptTool.cpp in J0EK3R/pxt-bleadv-common
 * (MIT License, Copyright (c) 2025 J0EK3R). See NOTICE.
 */
final class Mk6Crypt {

    private Mk6Crypt() {}

    private static int inv8(int v) {
        int r = 0;
        for (int i = 0; i < 8; i++) {
            if ((v & (1 << i)) != 0) r |= 1 << (7 - i);
        }
        return r;
    }

    private static int inv16(int v) {
        int r = 0;
        for (int i = 0; i < 16; i++) {
            if ((v & (1 << i)) != 0) r |= 1 << (15 - i);
        }
        return r;
    }

    private static int crcStep(int result) {
        for (int k = 0; k < 8; k++) {
            if ((result & 0x8000) == 0) {
                result = (result << 1) & 0xFFFF;
            } else {
                result = ((result << 1) ^ 0x1021) & 0xFFFF;
            }
        }
        return result;
    }

    private static int crc16(byte[] a1, byte[] a2) {
        int result = 0xFFFF;
        for (int i = 0; i < a1.length; i++) {
            result ^= ((a1[a1.length - 1 - i] & 0xFF) << 8) & 0xFFFF;
            result = crcStep(result);
        }
        for (int i = 0; i < a2.length; i++) {
            int c = inv8(a2[i] & 0xFF);
            result ^= (c << 8) & 0xFFFF;
            result = crcStep(result);
        }
        return (inv16(result) ^ 0xFFFF) & 0xFFFF;
    }

    private static int[] whiteningInit(int val) {
        return new int[] {
            1, (val >> 5) & 1, (val >> 4) & 1, (val >> 3) & 1, (val >> 2) & 1, (val >> 1) & 1, val & 1
        };
    }

    private static int whiteningOutput(int[] c) {
        int v3 = c[3];
        int v6 = c[6];
        c[3] = c[2];
        c[2] = c[1];
        c[1] = c[0];
        c[0] = c[6];
        c[6] = c[5];
        c[5] = c[4];
        c[4] = v3 ^ v6;
        return c[0];
    }

    private static void whiteningEncode(int[] data, int start, int len, int[] ctx) {
        for (int i = 0; i < len; i++) {
            int cur = data[start + i];
            int res = 0;
            for (int bit = 0; bit < 8; bit++) {
                int u = whiteningOutput(ctx);
                res = ((u ^ ((cur >> bit) & 1)) << bit) | res;
            }
            data[start + i] = res & 0xFF;
        }
    }

    /**
     * Builds the 24 bytes that follow the company id (0xFFF0) in the manufacturer
     * specific advertising field.
     */
    static byte[] rfPayload(byte[] addr, byte[] data, int ctxValue) {
        final int dataOffset = 0x12;
        final int inverseOffset = 0x0F;
        final int size = dataOffset + addr.length + data.length + 2;
        int[] buf = new int[size];

        buf[15] = 0x71;
        buf[16] = 0x0F;
        buf[17] = 0x55;

        for (int i = 0; i < addr.length; i++) {
            buf[i + dataOffset] = addr[addr.length - i - 1] & 0xFF;
        }
        for (int i = 0; i < data.length; i++) {
            buf[dataOffset + addr.length + i] = data[i] & 0xFF;
        }
        for (int i = inverseOffset; i < addr.length + dataOffset; i++) {
            buf[i] = inv8(buf[i]);
        }

        int crc = crc16(addr, data);
        buf[size - 2] = crc & 0xFF;
        buf[size - 1] = (crc >> 8) & 0xFF;

        whiteningEncode(buf, dataOffset, addr.length + data.length + 2, whiteningInit(0x3F));
        whiteningEncode(buf, 0, size, whiteningInit(ctxValue));

        final int len = addr.length + data.length + 5;
        byte[] out = new byte[24];
        for (int i = 0; i < len && i < 24; i++) {
            out[i] = (byte) buf[15 + i];
        }
        for (int i = len; i < 24; i++) {
            out[i] = (byte) (i + 1);
        }
        return out;
    }
}
