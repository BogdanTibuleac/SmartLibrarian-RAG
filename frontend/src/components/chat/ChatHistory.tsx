import React from "react";
import ChatMessage from "./ChatMessage";

interface Message {
    sender: "user" | "assistant";
    content: string;
}

interface ChatHistoryProps {
    messages: Message[];
}

const ChatHistory: React.FC<ChatHistoryProps> = ({ messages }) => {
    return (
        <div className="flex flex-col overflow-y-auto flex-grow p-4">
            {messages.map((msg, i) => (
                <ChatMessage key={i} sender={msg.sender} content={msg.content} />
            ))}
        </div>
    );
};

export default ChatHistory;
