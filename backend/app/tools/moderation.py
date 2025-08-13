import openai

def is_prompt_flagged(prompt: str) -> bool:
    try:
        result = openai.Moderation.create(input=prompt)
        return result["results"][0]["flagged"]
    except Exception as e:
        print(f"[Moderation] Warning: {e}")
        return False  # fail-safe: allow prompt
