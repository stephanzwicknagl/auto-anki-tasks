# anki-skills

Anki card maintenance script for Mandarin Chinese flashcard decks.

## What it does

1. **Reclassify sentence cards** — finds vocab cards in the Pleco deck that are actually sentences (ending in `。！？`) and moves them to the sentence deck with the correct note type.
2. **Add TTS audio** — generates Google Cloud TTS audio for any cards missing audio, using a Mandarin voice at a slightly slower speed for learning.

## Requirements

- [Anki](https://apps.ankiweb.net/) running with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on
- A Google Cloud account with the Text-to-Speech API enabled
- Python 3.x

```bash
pip install -r requirements.txt
```

Set up Google Cloud credentials:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
```

## Usage

```bash
# Run all operations
python maintain_cards.py

# Preview changes without applying them
python maintain_cards.py --dry-run

# Run only one operation
python maintain_cards.py --reclassify-only
python maintain_cards.py --audio-only

# Check field names match your note types
python maintain_cards.py --list-fields
```

## Configuration

Edit the constants at the top of `maintain_cards.py` to match your deck names and note types:

| Constant | Description |
|---|---|
| `PLECO_DECK` | Source deck for vocab cards |
| `PLECO_NOTE_TYPE` | Note type used in the Pleco deck |
| `SENTENCE_DECK` | Target deck for reclassified sentence cards |
| `SENTENCE_NOTE_TYPE` | Note type for sentence cards |
| `EXPRESSION_FIELD` | Field containing the Chinese text |
| `AUDIO_FIELD` | Field where audio is stored |
| `TTS_VOICE_NAME` | Google Cloud TTS voice |
| `TTS_SPEAKING_RATE` | Playback speed (1.0 = normal) |
