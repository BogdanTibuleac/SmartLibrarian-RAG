import React from "react";

type MessageType = "user" | "assistant";

interface ChatMessageProps {
    sender: MessageType;
    content: string;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ sender, content }) => {
    const isUser = sender === "user";

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-4`}>
            <div
                className={`max-w-xl px-4 py-3 text-base whitespace-pre-wrap rounded-xl shadow-sm ${isUser
                        ? "bg-slate-700 text-white rounded-br-none font-medium font-sans"
                        : "bg-slate-100 text-slate-800 rounded-bl-none font-serif"
                    }`}
            >
                {content}
            </div>

        </div>
    );
};

export default ChatMessage;
