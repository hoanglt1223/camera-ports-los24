package com.codex.rearlens;

import java.lang.reflect.Method;
import java.util.concurrent.ConcurrentHashMap;

/**
 * RearLens.call() scanned Class.getMethods() of the MIUI camera module on every call while
 * holding the RearLens class lock; the main thread's lens chip then waited on that lock (ANR).
 */
public final class MethodCache {
    private static final Object MISSING = new Object();
    private static final ConcurrentHashMap<String, Object> CACHE = new ConcurrentHashMap<>();

    private MethodCache() {
    }

    public static Method find(Class<?> cls, String name, int arity) {
        String key = cls.getName() + '#' + name + '#' + arity;
        Object hit = CACHE.get(key);
        if (hit == null) {
            hit = MISSING;
            for (Method m : cls.getMethods()) {
                if (m.getName().equals(name) && m.getParameterTypes().length == arity) {
                    m.setAccessible(true);
                    hit = m;
                    break;
                }
            }
            CACHE.put(key, hit);
        }
        return hit == MISSING ? null : (Method) hit;
    }
}
