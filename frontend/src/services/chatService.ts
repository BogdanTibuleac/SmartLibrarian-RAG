export interface ChatRequest {
    query: string;
}

export interface ChatResponse {
    recommended_title: string | null;
    explanation: string;
    source_summary: string | null;
    normalized_distance: number | null;
}

export async function sendChatMessage(message: string) {
    const response = await fetch("http://localhost:8000/chat/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: message }),
    });

    if (!response.ok) {
        throw new Error("Eroare la trimiterea cererii.");
    }

    return response.json();
}
