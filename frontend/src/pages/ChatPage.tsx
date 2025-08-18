// src/pages/ChatPage.tsx
import React, { useState } from "react";
import ChatHistory from "../components/chat/ChatHistory";
import ChatInput from "../components/chat/ChatInput";
import BookLoader from "../components/ui/BookLoader";
import { sendChatMessage, normalizePrompt } from "../services/chatService";

interface Message {
    sender: "user" | "assistant";
    content: string;
    promptNorm?: string;
    isImage?: boolean;               // <-- NEW
}

const ChatPage: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSend = async (message: string) => {
        setMessages((prev) => [...prev, { sender: "user", content: message }]);
        setLoading(true);
        try {
            const response = await sendChatMessage(message);
            const promptNorm = response.prompt_norm ?? normalizePrompt(message);
            const isImage = !!response.image_url;
            const content = response.image_url || response.explanation || " "; // prefer image

            setMessages((prev) => [
                ...prev,
                {
                    sender: "assistant",
                    content,
                    promptNorm,
                    isImage,                 // <-- carry to history/message
                },
            ]);
        } catch (err) {
            setMessages((prev) => [
                ...prev,
                {
                    sender: "assistant",
                    content: "❌ Eroare la comunicarea cu serverul.",
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            className="min-h-screen bg-center bg-cover bg-no-repeat flex items-center justify-center px-4"
            style={{
                backgroundImage: `
          radial-gradient(ellipse at center, rgba(71, 85, 105, 0.8) 0%, rgba(30, 41, 59, 0.9) 100%),
          url('/bg.jpg')
        `,
                backgroundBlendMode: "overlay",
            }}
        >
            <div className="relative w-full max-w-5xl h-screen flex flex-col bg-white/20 backdrop-blur-md shadow-2xl ring-1 ring-white/20 rounded-xl overflow-hidden">
                <header className="absolute inset-x-0 top-0 z-20 h-14 flex items-center justify-center bg-white/5 backdrop-blur-md border-b border-white/10">
                    <h1 className="text-white text-2xl font-bold tracking-wide drop-shadow">
                        Smart Librarian
                    </h1>
                </header>



                <ChatHistory messages={messages} />

                {loading && (
                    <div className="fixed inset-0 flex items-center justify-center bg-black/30 z-50">
                        <BookLoader />
                    </div>
                )}

                <ChatInput onSend={handleSend} loading={loading} />
            </div>
        </div>
    );
};

export default ChatPage;
