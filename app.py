from flask import Flask, request, jsonify
from cli.cli import run_ai   # adjust if needed

app = Flask(__name__)

# Home route (for browser)
@app.route("/")
def home():
    print("Evo-AI Version 2 🚀", flush=True)  # visible in docker logs

    return """
    <h2>Evo-AI Version 2 🚀</h2>
    <form method="post" action="/ask">
        <input name="input" placeholder="Ask something"/>
        <button type="submit">Send</button>
    </form>
    """

# API route
@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.form.get("input") or request.json.get("input")
    response = run_ai(user_input)
    return jsonify({"response": response})

# Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)