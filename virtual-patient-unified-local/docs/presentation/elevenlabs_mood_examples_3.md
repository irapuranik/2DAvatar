# ElevenLabs 3-Mood Slider Examples

These are three practical presets for the virtual patient voice, each paired with a generated MP3 sample.

## Mood Presets

1. Calm / Cooperative
   - stability: 0.78
   - similarity_boost: 0.82
   - style: 0.20
   - sample: `docs/presentation/audio/mood_calm.mp3`

2. Anxious / Worried
   - stability: 0.36
   - similarity_boost: 0.75
   - style: 0.68
   - sample: `docs/presentation/audio/mood_anxious.mp3`

3. Defensive / Irritable
   - stability: 0.46
   - similarity_boost: 0.72
   - style: 0.74
   - sample: `docs/presentation/audio/mood_defensive.mp3`

## Notes

- Keep the spoken text constant across moods for clean comparisons.
- If delivery sounds too flat, increase `style` by 0.05 to 0.10.
- If voice identity drifts, increase `similarity_boost` by 0.05.

## Contrast Set (Subtle -> Extreme)

These use the same sentence as the presets above, but maximize expressive contrast for demos.

1. Subtle
   - stability: 0.82
   - similarity_boost: 0.84
   - style: 0.12
   - sample: `docs/presentation/audio/mood_subtle.mp3`

2. Medium
   - stability: 0.55
   - similarity_boost: 0.78
   - style: 0.48
   - sample: `docs/presentation/audio/mood_medium.mp3`

3. Extreme
   - stability: 0.24
   - similarity_boost: 0.68
   - style: 0.90
   - sample: `docs/presentation/audio/mood_extreme.mp3`

## Emotion Set (Happy / Sad / Angry)

1. Happy
   - stability: 0.58
   - similarity_boost: 0.80
   - style: 0.72
   - sample: `docs/presentation/audio/mood_happy.mp3`

2. Sad
   - stability: 0.74
   - similarity_boost: 0.78
   - style: 0.30
   - sample: `docs/presentation/audio/mood_sad.mp3`

3. Angry
   - stability: 0.28
   - similarity_boost: 0.70
   - style: 0.88
   - sample: `docs/presentation/audio/mood_angry.mp3`

## Emotion-Matched Sentences (Happy / Sad / Angry)

Each mood uses a different line that semantically matches the intended emotion.

1. Happy
   - sentence: "That is wonderful news, and I am really glad we are making progress together today."
   - stability: 0.56
   - similarity_boost: 0.80
   - style: 0.74
   - sample: `docs/presentation/audio/mood_happy_sentence.mp3`

2. Sad
   - sentence: "I feel overwhelmed and tired, and it has been hard for me to stay hopeful lately."
   - stability: 0.76
   - similarity_boost: 0.78
   - style: 0.28
   - sample: `docs/presentation/audio/mood_sad_sentence.mp3`

3. Angry
   - sentence: "I am frustrated because no one seems to listen, and I am tired of repeating myself."
   - stability: 0.27
   - similarity_boost: 0.70
   - style: 0.90
   - sample: `docs/presentation/audio/mood_angry_sentence.mp3`

## Expressive Emotion Set (Higher Contrast)

Generated with `model_id: eleven_multilingual_v2` and stronger punctuation/prosody cues.

1. Happy (Expressive)
   - sentence: "This is amazing news! I feel so much lighter, and I am genuinely excited about what comes next!"
   - stability: 0.38
   - similarity_boost: 0.78
   - style: 0.95
   - sample: `docs/presentation/audio/mood_happy_expressive.mp3`

2. Sad (Expressive)
   - sentence: "I don't know... I feel exhausted, and honestly, it has been hard to keep going lately."
   - stability: 0.86
   - similarity_boost: 0.80
   - style: 0.08
   - sample: `docs/presentation/audio/mood_sad_expressive.mp3`

3. Angry (Expressive)
   - sentence: "No. I'm frustrated. I keep explaining this, and nobody is listening to me!"
   - stability: 0.16
   - similarity_boost: 0.68
   - style: 1.00
   - sample: `docs/presentation/audio/mood_angry_expressive.mp3`
