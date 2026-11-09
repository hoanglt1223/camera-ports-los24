package com.codex.filmlut;

import android.content.Context;
import com.codex.model120.AlexaLut;
import java.io.IOException;

/** Film-look LUT styles appended after the donor models (style ids 771..778). */
public final class FilmLut {
    public static final int FIRST = 771;
    static final String[] IDS = {
        "film-warm", "film-portrait", "film-chrome", "film-matte",
        "film-teal-orange", "film-vivid", "film-mono-hc", "film-mono-soft",
    };
    static final String[] NAMES = {
        "Warm Film", "Portrait Film", "Cool Chrome", "Faded Matte",
        "Teal & Orange", "Vivid Slide", "Mono Contrast", "Mono Soft",
    };
    static final String[] INTROS = {
        "Warm Film\nWarm balance, gentle S-curve, soft blacks",
        "Portrait Film\nLow contrast, warm skin, pastel greens",
        "Cool Chrome\nCool balance, crisp contrast, muted colour",
        "Faded Matte\nLifted blacks, rolled highlights, low saturation",
        "Teal & Orange\nTeal shadows, warm highlights",
        "Vivid Slide\nSlide-film contrast and saturation",
        "Mono Contrast\nBlack & white, red-filter weighting, hard curve",
        "Mono Soft\nBlack & white, soft curve, light warm tone",
    };

    private FilmLut() {
    }

    /** kind 0 = display names, 1 = sample file names, 2 = intro text. */
    public static String[] extend(String[] base, int kind) {
        String[] out = new String[base.length + IDS.length];
        System.arraycopy(base, 0, out, 0, base.length);
        for (int i = 0; i < IDS.length; i++) {
            out[base.length + i] = kind == 0 ? NAMES[i] : kind == 1 ? IDS[i] + ".jpg" : INTROS[i];
        }
        return out;
    }

    public static boolean owns(int style) {
        return style >= FIRST && style < FIRST + IDS.length;
    }

    public static byte[] process(Context context, byte[] jpeg, int style) throws IOException {
        byte[] out = AlexaLut.process(context, jpeg, "film/" + IDS[style - FIRST] + ".bin");
        if (out == null || out == jpeg || out.length < 4) {
            throw new IOException("Film LUT did not produce an image");
        }
        return out;
    }
}
