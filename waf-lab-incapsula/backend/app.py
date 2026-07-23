"""
Origin server for the WAF lab. This is the "real site" sitting behind the
simulated Incapsula-style WAF proxy (see ../waf-proxy/proxy.py). It has no
bot-detection logic of its own -- in the lab topology it should only ever be
reached through the proxy, which is what does the challenge/verification.
"""

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    return (
        "<h1>Protected Origin</h1>"
        "<p>You reached the real backend. In production this host would not "
        "be directly reachable -- only the WAF proxy's public IP would be.</p>"
        "<p>LAB_FLAG{waf_bypass_incapsula_lab}</p>"
    )


@app.get("/api/secret")
def secret():
    return jsonify({"flag": "LAB_FLAG{waf_bypass_incapsula_lab}", "status": "reached-origin"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
