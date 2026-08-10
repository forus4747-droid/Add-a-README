#!/usr/bin/env python3
"""Second opinion pass: send a YouTube tutorial to Gemini and get a build spec back.

Gemini reads the video natively, its own frames plus the audio, instead of reading
frames someone else picked. That makes it an independent witness to the same
tutorial your coding agent just watched.

usage:
  gemini_review.py <youtube-url-or-file> [--focus "the part I care about"]
                   [--samples 2] [--fps 1] [--start 0] [--end 600] [--key KEY]

Key: --key, else $GEMINI_API_KEY. Free key: https://aistudio.google.com/apikey
Install: pip install google-genai
"""
import argparse
import os
import sys
import time

from google import genai
from google.genai import types

# Falls forward until one answers. Free keys list pro models then 429 on call.
# If ALL of these fail, check the current model list rather than assuming the
# script is broken -- Gemini model naming moves faster than any script.
MODEL_CHAIN = ["gemini-flash-latest", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash"]

PROMPT = """You are writing a build spec for a coding agent that will reproduce what this tutorial teaches. The agent cannot watch video. Your text is the only thing it will have.

Focus: {focus}

Report exactly this, in this order:

1. WHAT IS BEING BUILT. One paragraph. The actual outcome, not the pitch.

2. STACK AND PREREQUISITES. Every tool, package, model, service and account that appears on screen or is named out loud. Give exact names and versions when they are visible. Mark anything that costs money.

3. COMMANDS AND CONFIG, VERBATIM. Every command typed into a terminal, every file path, every env var, every config value you can actually read on screen. Quote it exactly. If a value is blurred, truncated or scrolled past, write UNREADABLE rather than guessing it.

4. THE BUILD ORDER. The steps in the order they were performed, including any step that was undone or redone. Say plainly where the video skips ahead or cuts to a finished state.

5. GOTCHAS. Every error hit on screen, every warning given out loud, every "make sure you" aside. These are the highest value part of the spec.

6. WHAT THE VIDEO DOES NOT SHOW. The gaps a builder would fall into: setup done off camera, values pasted from somewhere unexplained, steps asserted but never demonstrated.

Rules:
- Describe only what is in THIS video. If something you would expect from a tutorial of this kind is absent, say it is absent. Do not fill it in from general knowledge.
- Prefer the exact string on screen over a paraphrase of it.
- Timestamps are your weakest output. Give them as rough markers only and never as a measurement."""


def resolve_key(cli_key):
    key = cli_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("No Gemini key. Pass --key or set GEMINI_API_KEY. Free key: https://aistudio.google.com/apikey")
    return key


def video_part(client, source, fps, start, end):
    meta = types.VideoMetadata(fps=fps, start_offset=f"{start}s", end_offset=f"{end}s")
    if source.startswith("http"):
        return types.Part(file_data=types.FileData(file_uri=source), video_metadata=meta)
    f = client.files.upload(file=source)
    while f.state.name == "PROCESSING":
        time.sleep(3)
        f = client.files.get(name=f.name)
    return types.Part(file_data=types.FileData(file_uri=f.uri, mime_type=f.mime_type), video_metadata=meta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="YouTube URL or local video file")
    ap.add_argument("--focus", default="the whole build, start to finish")
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--fps", type=int, default=1, help="frames per second Gemini samples")
    ap.add_argument("--start", type=int, default=0, help="start at N seconds")
    ap.add_argument("--end", type=int, default=600, help="stop at N seconds")
    ap.add_argument("--key", default=None)
    args = ap.parse_args()

    client = genai.Client(api_key=resolve_key(args.key))
    part = video_part(client, args.source, args.fps, args.start, args.end)
    prompt = PROMPT.format(focus=args.focus)

    got = 0
    for i in range(args.samples):
        for model in MODEL_CHAIN:
            try:
                r = client.models.generate_content(
                    model=model,
                    contents=types.Content(parts=[part, types.Part(text=prompt)]),
                )
                u = r.usage_metadata
                print(f"\n===== SAMPLE {i + 1}/{args.samples}  ({getattr(r, 'model_version', model)}, "
                      f"{u.prompt_token_count}+{u.thoughts_token_count or 0}+{u.candidates_token_count} tok) =====")
                print(r.text)
                got += 1
                break
            except Exception as e:
                msg = str(e)
                if "429" in msg or "404" in msg or "RESOURCE_EXHAUSTED" in msg:
                    print(f"[{model}] unavailable, trying next", file=sys.stderr)
                    continue
                raise
        else:
            print(f"[sample {i + 1}] all models unavailable (free-tier quota likely exhausted)", file=sys.stderr)
        time.sleep(2)

    if got:
        print("\n===== HOW TO READ THESE =====")
        print("Keep: tool names, command strings, error messages, and any claim that appears in BOTH samples.")
        print("Flag: anything that appears in only one sample. That is where the model is guessing.")
        print("Never trust: timestamps, counts, durations, version numbers it did not clearly read on screen.")


if __name__ == "__main__":
    main()
