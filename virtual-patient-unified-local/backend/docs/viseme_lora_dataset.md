# Viseme LoRA Dataset Spec

This project supports optional LoRA loading for local viseme generation via:

- `CUSTOM_LOCAL_LORA_DIR`
- `CUSTOM_LOCAL_LORA_SCALE`

Use this dataset format when preparing a LoRA that improves identity lock + mouth articulation.

## Directory layout

```
viseme_lora_dataset/
  images/
    avatar_A_0001.png
    avatar_B_0001.png
    avatar_C_0001.png
    ...
  metadata.jsonl
```

## `metadata.jsonl` schema

Each line:

```json
{"file_name":"images/avatar_F_0001.png","text":"solo portrait, same character, viseme F, jaw dropped wide open, white background","viseme":"F","identity_id":"avatar_01"}
```

Required fields:

- `file_name`: relative path to image
- `text`: training caption
- `viseme`: one of `A,B,C,D,E,F,G,H,X,blink`
- `identity_id`: character identity label

## Data collection rules

- Keep camera/framing/background fixed across visemes.
- Include at least 30-50 examples per viseme for one identity before training.
- Prefer 512x512 PNG images.
- Ensure mouth shape is clearly visible and exaggerated enough for `F/G/H`.
- Include `X` and `blink` examples; these stabilize idle and eye-closure behavior.

## Prompt template recommendation

Use consistent prompt scaffolding:

- `same character`
- `same pose`
- `same camera framing`
- `same lighting/colors`
- `white background`
- `viseme <key> mouth shape`

## Integration hook

At runtime, set:

```env
VISEME_IMAGE_BACKEND=local
CUSTOM_LOCAL_LORA_DIR=/absolute/path/to/lora/weights
CUSTOM_LOCAL_LORA_SCALE=0.8
```

The local generator automatically attempts to load/fuse LoRA weights for txt2img and img2img pipelines.
