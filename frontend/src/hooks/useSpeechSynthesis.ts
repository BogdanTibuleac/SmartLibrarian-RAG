// src/hooks/useSpeechSynthesis.ts
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type TTSConfig = {
    rate?: number;   // 0.1 – 10 (1 = normal)
    pitch?: number;  // 0 – 2   (1 = normal)
    volume?: number; // 0 – 1   (1 = normal)
    voiceMatcher?: (v: SpeechSynthesisVoice) => boolean; // choose voice
};

export type TTSState = {
    supported: boolean;
    speaking: boolean;
    paused: boolean;
    voices: SpeechSynthesisVoice[];
};

export function useSpeechSynthesis(config?: TTSConfig) {
    const synthesisRef = useRef<SpeechSynthesis | null>(null);
    const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
    const [speaking, setSpeaking] = useState(false);
    const [paused, setPaused] = useState(false);

    // SSR guard
    const supported = typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;

    // hydrate refs once
    useEffect(() => {
        if (!supported) return;
        synthesisRef.current = window.speechSynthesis;

        const loadVoices = () => {
            const v = window.speechSynthesis.getVoices?.() ?? [];
            setVoices(v);
        };

        loadVoices();
        // Some browsers populate voices async
        window.speechSynthesis.onvoiceschanged = loadVoices;

        return () => {
            if (window) window.speechSynthesis.onvoiceschanged = null;
        };
    }, [supported]);

    // AFTER
    const defaultVoice = useMemo<SpeechSynthesisVoice | null>(() => {
        if (!voices.length) return null;
        const ro = voices.find(v => v.lang?.toLowerCase().startsWith("ro"));
        if (ro) return ro;
        const en = voices.find(v => v.lang?.toLowerCase().startsWith("en"));
        if (en) return en;
        return voices[0] ?? null;
    }, [voices]);


    const speak = useCallback(
        (text: string, override?: Partial<TTSConfig>) => {
            if (!supported || !synthesisRef.current) return;

            // Cancel anything currently in flight
            synthesisRef.current.cancel();

            const u = new SpeechSynthesisUtterance(text.trim());
            const rate = override?.rate ?? config?.rate ?? 1;
            const pitch = override?.pitch ?? config?.pitch ?? 1;
            const volume = override?.volume ?? config?.volume ?? 1;
            const match = override?.voiceMatcher ?? config?.voiceMatcher;

            u.rate = Math.max(0.1, Math.min(rate, 10));
            u.pitch = Math.max(0, Math.min(pitch, 2));
            u.volume = Math.max(0, Math.min(volume, 1));
            u.voice = match
                ? voices.find(match) ?? defaultVoice
                : defaultVoice;

            u.onstart = () => { setSpeaking(true); setPaused(false); };
            u.onpause = () => setPaused(true);
            u.onresume = () => setPaused(false);
            u.onend = () => { setSpeaking(false); setPaused(false); };
            u.onerror = () => { setSpeaking(false); setPaused(false); };

            synthesisRef.current.speak(u);
        },
        [config?.pitch, config?.rate, config?.volume, config?.voiceMatcher, defaultVoice, supported, voices]
    );

    const pause = useCallback(() => {
        const s = synthesisRef.current;
        if (!supported || !s) return;
        if (s.speaking && !s.paused) { s.pause(); setPaused(true); }
    }, [supported]);

    const resume = useCallback(() => {
        const s = synthesisRef.current;
        if (!supported || !s) return;
        if (s.paused) { s.resume(); setPaused(false); }
    }, [supported]);

    const cancel = useCallback(() => {
        const s = synthesisRef.current;
        if (!supported || !s) return;
        s.cancel();
        setSpeaking(false);
        setPaused(false);
    }, [supported]);

    // Safety: cancel on unmount
    useEffect(() => () => cancel(), [cancel]);

    const state: TTSState = { supported, speaking, paused, voices };
    return { ...state, speak, pause, resume, cancel };
}
