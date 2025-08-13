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
            className="flex items-center gap-3 border-t border-slate-200 p-4 bg-white/80 backdrop-blur-md"
        >
            <input
                className="flex-grow px-4 py-2 rounded-md border border-slate-300 bg-slate-100 text-slate-800 placeholder-slate-500 shadow-inner focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition font-serif"
                type="text"
                placeholder="Scrie o întrebare despre o carte..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
            />
            <button
                type="submit"
                disabled={loading}
                className="bg-slate-700 text-white px-5 py-2 rounded-md font-medium hover:bg-slate-800 transition disabled:opacity-50"
            >
                Trimite
            </button>
        </form>
    );
};

export default ChatInput;
