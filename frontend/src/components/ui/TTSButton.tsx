// src/components/TTSButton.tsx
import { memo } from "react";
import { useSpeechSynthesis } from "../../hooks/useSpeechSynthesis";

type Props = {
    text: string;                 // the recommendation to read aloud
    className?: string;           // Tailwind hooks
    langHint?: "ro" | "en";       // optional language hint
};

const TTSButton = memo(({ text, className, langHint }: Props) => {
    const { supported, speaking, paused, speak, pause, resume, cancel, voices } =
        useSpeechSynthesis({
            // Prefer Romanian voice if langHint="ro"
            voiceMatcher: langHint
                ? (v) => v.lang?.toLowerCase().startsWith(langHint)
                : undefined,
            rate: 1.0,
            pitch: 1.0,
            volume: 1.0,
        });

    if (!supported) {
        return (
            <button
                type="button"
                className={`opacity-60 cursor-not-allowed ${className ?? ""}`}
                aria-disabled
                title="Text‑to‑speech not supported in this browser."
            >
                🔇 TTS
            </button>
        );
    }

    const onPlay = () => speak(text);
    const onPause = () => pause();
    const onResume = () => resume();
    const onStop = () => cancel();

    return (
        <div className={`inline-flex items-center gap-2 ${className ?? ""}`}>
            {!speaking && (
                <button
                    type="button"
                    onClick={onPlay}
                    className="rounded-md border px-3 py-1 text-sm hover:bg-black/5"
                    aria-label="Play recommendation"
                    title={`Play (${voices.length ? "voice available" : "loading voices..."})`}
                >
                    🔊 Play
                </button>
            )}
            {speaking && !paused && (
                <>
                    <button
                        type="button"
                        onClick={onPause}
                        className="rounded-md border px-3 py-1 text-sm hover:bg-black/5"
                        aria-label="Pause"
                        title="Pause"
                    >
                        ⏸ Pause
                    </button>
                    <button
                        type="button"
                        onClick={onStop}
                        className="rounded-md border px-3 py-1 text-sm hover:bg-black/5"
                        aria-label="Stop"
                        title="Stop"
                    >
                        ⏹ Stop
                    </button>
                </>
            )}
            {speaking && paused && (
                <>
                    <button
                        type="button"
                        onClick={onResume}
                        className="rounded-md border px-3 py-1 text-sm hover:bg-black/5"
                        aria-label="Resume"
                        title="Resume"
                    >
                        ▶️ Resume
                    </button>
                    <button
                        type="button"
                        onClick={onStop}
                        className="rounded-md border px-3 py-1 text-sm hover:bg-black/5"
                        aria-label="Stop"
                        title="Stop"
                    >
                        ⏹ Stop
                    </button>
                </>
            )}
        </div>
    );
});

export default TTSButton;
