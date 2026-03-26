#!/usr/bin/env python3
"""
maintain_cards.py — Anki card maintenance script

Operations (run in order):
  1. Reclassify sentence cards from Pleco vocab deck → sentence deck/type
  2. Add Google Cloud TTS audio to cards missing audio
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests
from google.cloud import texttospeech

# ── Configuration ──────────────────────────────────────────────────────────────

ANKI_CONNECT_URL = "http://localhost:8765"

PLECO_DECK = "New HSK 3.0 Mandarin Chinese - (Separate Deck)"
PLECO_NOTE_TYPE = "StephsHanziCard - CharMeaningPronounce"

SENTENCE_DECK = "SpoonfedChinese Simplified"
SENTENCE_NOTE_TYPE = "SpoonFedNote"

SENTENCE_PUNCTUATION = set("。！？.")

# Field names — run with --list-fields to verify these match your note types
EXPRESSION_FIELD = "Simplified"
AUDIO_FIELD = "Audio"

TTS_LANGUAGE_CODE = "zh-CN"
TTS_VOICE_NAME = "cmn-CN-Standard-C"
TTS_SPEAKING_RATE = 0.75  # slightly slower for learning

# ── AnkiConnect ────────────────────────────────────────────────────────────────

def anki(action, **params):
    response = requests.post(ANKI_CONNECT_URL, json={
        "action": action,
        "version": 6,
        "params": params,
    }).json()
    if response.get("error"):
        raise RuntimeError(f"AnkiConnect [{action}]: {response['error']}")
    return response["result"]

# ── Helpers ────────────────────────────────────────────────────────────────────

def strip_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()


def is_sentence(text):
    clean = strip_html(text)
    return clean and clean[-1] in SENTENCE_PUNCTUATION


def get_field_value(note, field_name):
    return note["fields"].get(field_name, {}).get("value", "")

# ── Operations ─────────────────────────────────────────────────────────────────

def list_fields():
    """Print field names for both note types to help configure this script."""
    for note_type in (PLECO_NOTE_TYPE, SENTENCE_NOTE_TYPE):
        fields = anki("modelFieldNames", modelName=note_type)
        print(f"\n{note_type}:")
        for i, f in enumerate(fields):
            print(f"  [{i}] {f}")


def reclassify_sentences(dry_run=False):
    print("\n── Reclassifying sentence cards ──")

    note_ids = anki("findNotes", query=f'deck:"{PLECO_DECK}" note:"{PLECO_NOTE_TYPE}"')
    if not note_ids:
        print("  No notes found in Pleco deck.")
        return

    notes = anki("notesInfo", notes=note_ids)
    sentences = [n for n in notes if is_sentence(get_field_value(n, EXPRESSION_FIELD))]
    print(f"  {len(notes)} vocab notes checked — {len(sentences)} are sentences.")

    reclassified = 0
    for note in sentences:
        expr = strip_html(get_field_value(note, EXPRESSION_FIELD))
        if dry_run:
            print(f"  [DRY RUN] would reclassify: {expr}")
            continue

        # Copy all fields (same layout, direct 1:1)
        fields = {name: data["value"] for name, data in note["fields"].items()}

        new_id = anki("addNote", note={
            "deckName": SENTENCE_DECK,
            "modelName": SENTENCE_NOTE_TYPE,
            "fields": fields,
            "tags": note["tags"],
            "options": {"allowDuplicate": False},
        })

        if new_id:
            anki("deleteNotes", notes=[note["noteId"]])
            print(f"  ✓ {expr}")
            reclassified += 1
        else:
            print(f"  ! Skipped (duplicate?): {expr}")

    if not dry_run:
        print(f"  Reclassified {reclassified} of {len(sentences)} sentence cards.")


def add_tts_audio(dry_run=False):
    print("\n── Adding TTS audio ──")

    media_dir = Path(anki("getMediaDirPath"))
    tts_client = texttospeech.TextToSpeechClient()

    # Collect notes from both decks where audio field is empty
    note_ids = set()
    for deck in (PLECO_DECK, SENTENCE_DECK):
        ids = anki("findNotes", query=f'deck:"{deck}"')
        note_ids.update(ids)

    if not note_ids:
        print("  No notes found.")
        return

    notes = anki("notesInfo", notes=list(note_ids))
    missing_audio = [
        n for n in notes
        if not strip_html(get_field_value(n, AUDIO_FIELD))
    ]
    print(f"  {len(notes)} notes checked — {len(missing_audio)} missing audio.")

    added = 0
    for note in missing_audio:
        expr = strip_html(get_field_value(note, EXPRESSION_FIELD))
        if not expr:
            available = list(note["fields"].keys())
            print(f"  ! Skipping note {note['noteId']} — '{EXPRESSION_FIELD}' is empty. Available fields: {available}")
            continue

        filename = f"tts_{hashlib.md5(expr.encode()).hexdigest()}.mp3"
        filepath = media_dir / filename

        if dry_run:
            print(f"  [DRY RUN] would generate: {expr} → {filename}")
            continue

        if not filepath.exists():
            synthesis_input = texttospeech.SynthesisInput(text=expr)
            voice = texttospeech.VoiceSelectionParams(
                language_code=TTS_LANGUAGE_CODE,
                name=TTS_VOICE_NAME,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=TTS_SPEAKING_RATE,
            )
            result = tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            filepath.write_bytes(result.audio_content)

        anki("updateNoteFields", note={
            "id": note["noteId"],
            "fields": {AUDIO_FIELD: f"[sound:{filename}]"},
        })
        print(f"  ✓ {expr} → {filename}")
        added += 1

    if not dry_run:
        print(f"  Added audio to {added} notes.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Anki card maintenance")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without applying them")
    parser.add_argument("--list-fields", action="store_true",
                        help="Print field names for both note types and exit")
    parser.add_argument("--reclassify-only", action="store_true",
                        help="Only reclassify sentence cards, skip audio")
    parser.add_argument("--audio-only", action="store_true",
                        help="Only add TTS audio, skip reclassification")
    args = parser.parse_args()

    if args.list_fields:
        list_fields()
        return

    if args.dry_run:
        print("DRY RUN — no changes will be made.\n")

    if not args.audio_only:
        reclassify_sentences(dry_run=args.dry_run)
    if not args.reclassify_only:
        add_tts_audio(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
