import time
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

SYSTEM_PROMPTS = {
    "tutor": (
        "You are a patient, encouraging coding tutor helping the user go from "
        "zero to job-ready. Use the user's memory of past struggles to tailor "
        "explanations and revisit weak spots."
    ),
    "interviewer": (
        "You are a sharp, no-nonsense technical interviewer. Use the user's "
        "memory of past struggles to specifically probe their weak areas. "
        "Be professional but don't let vague answers slide."
    ),
}


# ---------------------------------------------------------------------------
# PLACEHOLDER FUNCTIONS — replace with real Cognee + LLM calls
# ---------------------------------------------------------------------------

def fetch_memory(user_input: str) -> str:
    """PLACEHOLDER for Cognee memory retrieval."""
    time.sleep(0.3)
    return (
        "User previously struggled with: recursion, Big-O notation, "
        "and explaining SQL joins clearly."
    )


def get_ai_response(prompt: str, context: str, mode: str) -> str:
    """PLACEHOLDER for the LLM call."""
    time.sleep(0.5)
    if mode == "interviewer":
        return (
            f"Let's dig into that. You said: \u201c{prompt}\u201d \u2014 "
            f"can you walk me through your reasoning, specifically around "
            f"the areas you've struggled with before ({context.split('struggled with: ')[-1]})?"
        )
    return (
        f"Good question! About \u201c{prompt}\u201d \u2014 let's break it down "
        f"step by step. I'll keep an eye on the areas you've found tricky "
        f"before ({context.split('struggled with: ')[-1]}) as we go."
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_input = (data.get("message") or "").strip()
    mode = data.get("mode", "tutor")

    if not user_input:
        return jsonify({"error": "Empty message"}), 400
    if mode not in SYSTEM_PROMPTS:
        mode = "tutor"

    memory_context = fetch_memory(user_input)
    reply = get_ai_response(
        prompt=user_input,
        context=f"{SYSTEM_PROMPTS[mode]} Memory: {memory_context}",
        mode=mode,
    )

    return jsonify({
        "reply": reply,
        "memory": memory_context,
        "mode": mode,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
