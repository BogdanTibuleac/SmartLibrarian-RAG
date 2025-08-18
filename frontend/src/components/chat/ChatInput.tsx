import React, { useState } from "react";

interface ChatInputProps {
    onSend: (message: string) => void;
    loading: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, loading }) => {
    const [input, setInput] = useState("");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            onSend(input);
            setInput("");
        }
    };

    return (
        <form
            onSubmit={handleSubmit}
            className="flex items-center gap-3 border-t border-slate-200 p-4 bg-transparent backdrop-blur-lg"
        >
            <input
                className={`flex-grow px-4 py-2 rounded-full border border-slate-300 text-slate-800 placeholder-slate-600 shadow-inner focus:outline-none focus:ring-2 focus:ring-slate-400 transition font-serif backdrop-blur-sm ${input.length > 0
                    ? "bg-white/70"
                    : "bg-white/20 focus:bg-white/70"
                    }`}
                type="text"
                placeholder="Scrie o întrebare despre o carte..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
            />
            <button
                type="submit"
                disabled={loading}
                className="flex items-center justify-center w-11 h-11 rounded-full bg-gradient-to-r from-slate-700 to-slate-900 shadow-md hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200 disabled:opacity-50 disabled:scale-100"
            >
                <img
                    src="/send.png"
                    alt="Trimite"
                    className="w-5 h-5 invert"
                />
            </button>
        </form>
    );
};

export default ChatInput;
