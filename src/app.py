from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any, List

import requests
from flask import Flask, jsonify, request

from pipeline import load_props, enrich_props

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

ASSETS_DIR = os.environ.get("ASSETS_DIR", "assets")
DEFAULT_PROPS_FILE = os.environ.get("PROPS_FILE", "sample_props.csv")
PORT = int(os.environ.get("PORT", "8080"))

# vLLM configuration (optional)
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL")  # e.g. "http://llm:8000"
VLLM_MODEL = os.environ.get("VLLM_MODEL", "mistral-7b-instruct")

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ------------------------------------------------------------------------------
# vLLM helper (optional)
# ------------------------------------------------------------------------------

def get_llm_explanation(prop: Dict[str, Any]) -> str:
    """
    Call a vLLM/OpenAI-compatible server to generate a concise explanation
    of the prop.

    If VLLM_BASE_URL is not configured or the request fails, a short
    fallback message is returned so the API still works.
    """
    if not VLLM_BASE_URL:
        return "LLM explanation not available (VLLM_BASE_URL is not configured)."

    url = VLLM_BASE_URL.rstrip("/") + "/v1/chat/completions"

    prompt = f"""
You are an NBA betting assistant. Explain this player prop in 2–3 sentences
for a casual sports bettor.

Player: {prop.get('player')}
Stat line: {prop.get('stat_line')}
American odds: {prop.get('american_odds')}
Implied probability: {prop.get('implied_prob'):.3f}
Estimated true probability: {prop.get('true_prob'):.3f}
Expected value per $1: {prop.get('ev_per_dollar'):.3f}

Mention whether this seems like a positive or negative value bet and why,
using simple language. Do not give gambling advice; just describe the numbers.
""".strip()

    payload = {
        "model": VLLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a concise NBA betting assistant."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 160,
        "temperature": 0.3,
    }

    try:
        resp = requests.post(url, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("vLLM call failed: %s", e)
        return "LLM explanation could not be generated due to an error."


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health() -> tuple:
    """
    Simple health check endpoint.
    """
    return jsonify({"status": "ok"}), 200


@app.route("/analyze", methods=["GET"])
def analyze() -> tuple:
    """
    Analyze props and return their implied probability, "true" probability,
    and expected value.

    Query parameters:
      - min_ev (float, optional): minimum EV per $1 to include. Default: 0.0
      - explain (bool, optional): if "true", try to attach an LLM explanation
        for the top few props (requires VLLM_BASE_URL).

    Example:
      GET /analyze?min_ev=0.05&explain=true
    """
    # Parse query parameters
    min_ev_str = request.args.get("min_ev", "0.0")
    explain_str = request.args.get("explain", "false").lower()

    try:
        min_ev = float(min_ev_str)
    except ValueError:
        return jsonify({"error": "min_ev must be a number"}), 400

    explain = explain_str in ("true", "1", "yes", "y")

    # Load and enrich props
    csv_path = os.path.join(ASSETS_DIR, DEFAULT_PROPS_FILE)
    try:
        df = load_props(csv_path)
    except Exception as e:
        logger.error("Error loading CSV: %s", e)
        return jsonify({"error": f"Failed to load props CSV: {e}"}), 500

    enriched = enrich_props(df)

    # Filter by EV
    filtered = enriched[enriched["ev_per_dollar"] >= min_ev]
    records: List[Dict[str, Any]] = filtered.to_dict(orient="records")

    # Optionally call vLLM for the top K props
    if explain and records:
        logger.info("Generating LLM explanations via vLLM...")
        # Sort by EV descending, explain top K to limit latency
        records_sorted = sorted(records, key=lambda r: r["ev_per_dollar"], reverse=True)
        top_k = min(3, len(records_sorted))

        for r in records_sorted[:top_k]:
            r["llm_explanation"] = get_llm_explanation(r)

        # Note: r is a dict shared with 'records', so the explanations
        # are visible in the main list as well.

    return jsonify(records), 200


# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Run the development server when executed directly
    app.run(host="0.0.0.0", port=PORT, debug=True)

