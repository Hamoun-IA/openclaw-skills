#!/usr/bin/env python3
"""Generate companion images using reference photo + scene prompt.

Supports: Google Imagen (Nano Banana Pro), Grok (xAI).

Usage:
  # Generate with Google Imagen
  presence_generate.py --prompt "Taking a selfie at a cozy café, evening, winter coat" --provider google

  # Generate with Grok
  presence_generate.py --prompt "Morning yoga on a balcony, sunrise" --provider grok

  # With explicit reference photo
  presence_generate.py --prompt "..." --reference assets/reference/face.jpg

  # Save to specific path
  presence_generate.py --prompt "..." --output /tmp/selfie.jpg
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

CONFIG_FILE = "persistent-memory.json"

def load_config():
    """Load config for defaults."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def find_reference_photo(explicit_path=None):
    """Find the reference photo."""
    candidates = [
        explicit_path,
        "assets/reference/face.jpg",
        "assets/reference/face.png",
        os.path.expanduser("~/.openclaw/skills/persistent-memory/assets/reference/face.jpg"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def generate_google(prompt, reference_path, output_path, model="imagen-3.0-generate-002"):
    """Generate image using Google Imagen API."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Build the request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}"

    # If reference photo exists, include it
    parts = [{"text": prompt}]
    if reference_path:
        with open(reference_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(reference_path)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        parts.insert(0, {"inlineData": {"mimeType": mime, "data": ref_b64}})
        parts.insert(0, {"text": "Generate an image of this person in the following scene. Keep the face identical to the reference photo."})

    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1}
    }

    # Try the generateContent endpoint for multimodal
    if reference_path:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
        }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

            # Extract image from response
            image_data = None
            if "candidates" in result:
                for part in result["candidates"][0].get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        image_data = part["inlineData"]["data"]
                        break
            elif "predictions" in result:
                image_data = result["predictions"][0].get("bytesBase64Encoded")

            if image_data:
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(image_data))
                print(f"OK: Image generated → {output_path}")
                return output_path
            else:
                print(f"ERROR: No image in response", file=sys.stderr)
                print(f"Response: {json.dumps(result)[:500]}", file=sys.stderr)
                sys.exit(1)

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Google API {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(1)

def generate_grok(prompt, reference_path, output_path):
    """Generate image using Grok/xAI API."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("ERROR: XAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    url = "https://api.x.ai/v1/images/generations"

    full_prompt = prompt
    if reference_path:
        full_prompt = f"Generate a photorealistic image matching this description. The person should look exactly like the reference. Scene: {prompt}"

    payload = {
        "model": "grok-2-image",
        "prompt": full_prompt,
        "n": 1,
        "response_format": "b64_json"
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            image_data = result["data"][0]["b64_json"]

            with open(output_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            print(f"OK: Image generated → {output_path}")
            return output_path

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Grok API {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Generate companion images")
    parser.add_argument("--prompt", required=True, help="Scene description")
    parser.add_argument("--provider", default="google", choices=["google", "grok"])
    parser.add_argument("--reference", help="Path to reference photo (auto-detected if not given)")
    parser.add_argument("--output", help="Output image path")
    parser.add_argument("--model", help="Override model")
    args = parser.parse_args()

    # Find reference photo
    ref = find_reference_photo(args.reference)
    if ref:
        print(f"Reference photo: {ref}")
    else:
        print("WARN: No reference photo found. Face consistency may vary.", file=sys.stderr)

    # Default output path
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = args.output or f"presence_{now}.jpg"

    if args.provider == "google":
        generate_google(args.prompt, ref, output, args.model or "imagen-3.0-generate-002")
    elif args.provider == "grok":
        generate_grok(args.prompt, ref, output)

if __name__ == "__main__":
    main()
