from flask import Flask, request, jsonify
from cli.cli import run_ai   # <-- adjust this

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("input")
    response = run_ai(user_input)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)