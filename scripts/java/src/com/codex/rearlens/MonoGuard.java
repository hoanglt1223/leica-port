package com.codex.rearlens;

import android.hardware.camera2.CameraCharacteristics;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Keeps monochrome sensors out of the lens plan. CameraCatalog.color() only rejected the MONOCHROME
 * capability, but HALs such as gauguin's report the 2 MP depth sensor (id 4) with a MONO colour filter
 * and no such capability, and expose it inside a logical bokeh camera (id 5 = 0 + 4). Routing 1x
 * through that logical camera gave a grayscale preview, and auto-detect offered the depth sensor as a
 * zoom stop.
 */
public final class MonoGuard {
    private static final Set<String> MONO = Collections.synchronizedSet(new java.util.HashSet<String>());

    private MonoGuard() {
    }

    static boolean mono(CameraCharacteristics c) {
        if (c == null) {
            return false;
        }
        try {
            Integer cfa = c.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT);
            return cfa != null && (cfa == 5 || cfa == 6); // MONO, NIR
        } catch (RuntimeException e) {
            return false;
        }
    }

    /** A mono sensor, or a logical camera with a mono physical child. */
    public static boolean excluded(CameraCharacteristics c) {
        if (mono(c)) {
            return true;
        }
        try {
            for (String child : c.getPhysicalCameraIds()) {
                if (MONO.contains(child)) {
                    return true;
                }
            }
        } catch (RuntimeException | LinkageError ignored) {
        }
        return false;
    }

    public static void prune(Map<String, CameraCharacteristics> info, Set<String> openIds, Set<String> publicIds,
                             Map<String, List<String>> parents) {
        for (Map.Entry<String, CameraCharacteristics> e : info.entrySet()) {
            if (mono(e.getValue())) {
                MONO.add(e.getKey());
            }
        }
        for (Map.Entry<String, CameraCharacteristics> e : info.entrySet()) {
            if (excluded(e.getValue())) {
                String id = e.getKey();
                openIds.remove(id);
                publicIds.remove(id);
                parents.remove(id);
                for (List<String> list : parents.values()) {
                    list.remove(id);
                }
            }
        }
        Iterator<Map.Entry<String, List<String>>> it = parents.entrySet().iterator();
        while (it.hasNext()) {
            if (it.next().getValue().isEmpty()) {
                it.remove();
            }
        }
    }
}
