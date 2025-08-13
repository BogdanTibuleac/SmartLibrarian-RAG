import React, { useState } from "react";
import ChatHistory from "../components/chat/ChatHistory";
import ChatInput from "../components/chat/ChatInput";
import BookLoader from "../components/ui/BookLoader";
import { sendChatMessage } from "../services/chatService";

interface Message {
    sender: "user" | "assistant";
    content: string;
}

const ChatPage: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSend = async (message: string) => {
        setMessages((prev) => [...prev, { sender: "user", content: message }]);
        setLoading(true);
        try {
            const response = await sendChatMessage(message);
            setMessages((prev) => [
                ...prev,
                {
                    sender: "assistant",
                    content: response.explanation,
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
                backgroundBlendMode: 'overlay',
            }}

        >
            <div className="w-full max-w-5xl h-screen flex flex-col bg-white/90 backdrop-blur-sm shadow-2xl ring-1 ring-slate-300 rounded-xl overflow-hidden">
                <header className="p-4 text-xl font-bold text-black border-b text-center shadow-sm bg-white/80 backdrop-blur-md">
                    Smart Librarian
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
