// src/services/chatService.ts
export interface ChatRequest {
    query: string;
}

export interface ChatResponse {
    recommended_title: string | null;
    explanation?: string;           // make optional so image-only responses are valid
    source_summary?: string | null;
    normalized_distance?: number | null;
    prompt_norm?: string;
    from_cache?: boolean;
    model_name?: string;
    generation_cost_usd?: number;
    image_url?: string;             // <-- NEW: backend returns this for image responses
}

export type Thumb = "up" | "down";

export const normalizePrompt = (s: string) =>
    s.trim().toLowerCase().replace(/\s+/g, " ");

export async function sendChatMessage(message: string): Promise<ChatResponse> {
    const response = await fetch("http://localhost:8000/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: message }),
    });

    if (!response.ok) {
        throw new Error("Eroare la trimiterea cererii.");
    }
    return response.json();
}

export async function postFeedback(promptNorm: string, thumb: Thumb) {
    const response = await fetch("http://localhost:8000/api/feedback/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt_norm: promptNorm, thumb }),
    });
    if (!response.ok) {
        throw new Error("Eroare la trimiterea feedback-ului.");
    }
    return response.json();
}
