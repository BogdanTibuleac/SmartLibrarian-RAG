// src/components/chat/ChatMessage.tsx
import React, { useState } from "react";
import ReactionButton from "../ui/ReactionButton";
import { postFeedback, type Thumb } from "../../services/chatService";
import TTSButton from "../ui/TTSButton";

type MessageType = "user" | "assistant";

interface ChatMessageProps {
    sender: MessageType;
    content: string;
    promptNorm?: string;
    isImage?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
    sender,
    content,
    promptNorm,
    isImage = false,
}) => {
    const isUser = sender === "user";

    const [sending, setSending] = useState(false);
    const [thumb, setThumb] = useState<Thumb | null>(null);

    const canReact = !isUser && !!promptNorm;
    const showTTS = !isUser && !isImage && content.trim().length > 0;
    const langHint: "ro" | "en" = /[ăâîșşțţ]/i.test(content) ? "ro" : "en";

    const handleVote = async (vote: Thumb) => {
        if (!promptNorm || sending || thumb === vote) return;
        setSending(true);
        setThumb(vote);
        try {
            await postFeedback(promptNorm, vote);
        } catch (err) {
            console.error(err);
            setThumb(null);
        } finally {
            setSending(false);
        }
    };

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-4`}>
            <div
                className={`max-w-xl px-4 py-3 text-base whitespace-pre-wrap rounded-xl shadow-sm ${isUser
                        ? "bg-slate-700 text-white rounded-br-none font-medium font-sans"
                        : "bg-slate-100 text-slate-800 rounded-bl-none font-serif"
                    }`}
            >
                {isImage ? (
                    <img
                        src={content}
                        alt="Generated visual"
                        className="rounded-lg shadow-md max-w-full"
                    />
                ) : (
                    content
                )}

                {/* Reactions + TTS in one line */}
                {(canReact || showTTS) && (
                    <div className="flex items-center gap-2 mt-2">
                        {canReact && (
                            <>
                                <ReactionButton
                                    variant="like"
                                    onClick={() => handleVote("up")}
                                    disabled={sending}
                                    selected={thumb === "up"}
                                />
                                <ReactionButton
                                    variant="dislike"
                                    onClick={() => handleVote("down")}
                                    disabled={sending}
                                    selected={thumb === "down"}
                                />
                                {thumb && (
                                    <span className="text-xs text-slate-500 ml-1">
                                        {thumb === "up" ? "Saved" : "Dismissed"}
                                    </span>
                                )}
                            </>
                        )}
                        {showTTS && (
                            <TTSButton text={content} langHint={langHint} />
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ChatMessage;
