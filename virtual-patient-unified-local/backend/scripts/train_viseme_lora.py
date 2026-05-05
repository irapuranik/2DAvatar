"""
Train a LoRA adapter on SD1.5 for viseme-specific mouth articulation.

Uses the dataset built by build_lora_dataset.py.

Usage:
    python scripts/train_viseme_lora.py [--epochs 50] [--lr 1e-4] [--rank 8] [--batch-size 1]

Output lands in backend/lora_weights/ — set CUSTOM_LOCAL_LORA_DIR to that path.
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR / "viseme_lora_dataset"
OUTPUT_DIR = BACKEND_DIR / "lora_weights"
BASE_MODEL = "runwayml/stable-diffusion-v1-5"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--rank", type=int, default=4, help="LoRA rank (lower = smaller adapter)")
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--resolution", type=int, default=256)
    p.add_argument("--gradient-accumulation", type=int, default=2)
    p.add_argument("--save-every", type=int, default=10, help="Save checkpoint every N epochs")
    p.add_argument("--model", type=str, default=BASE_MODEL)
    p.add_argument("--dataset", type=str, default=str(DATASET_DIR))
    p.add_argument("--output", type=str, default=str(OUTPUT_DIR))
    return p.parse_args()


def main():
    args = parse_args()
    dataset_dir = Path(args.dataset)
    output_dir = Path(args.output)
    meta_path = dataset_dir / "metadata.jsonl"

    if not meta_path.is_file():
        logger.error(f"metadata.jsonl not found at {meta_path}. Run build_lora_dataset.py first.")
        sys.exit(1)

    with open(meta_path) as f:
        entries = [json.loads(line) for line in f if line.strip()]
    logger.info(f"Dataset: {len(entries)} entries from {meta_path}")

    import torch
    import torchvision.transforms as T
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset
    from diffusers import AutoPipelineForText2Image
    from peft import LoraConfig, get_peft_model

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.float32  # MPS needs float32 for training
    logger.info(f"Device: {device}, dtype: {dtype}")

    logger.info(f"Loading base model: {args.model}")
    pipe = AutoPipelineForText2Image.from_pretrained(
        args.model,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )

    text_encoder = pipe.text_encoder
    tokenizer = pipe.tokenizer
    unet = pipe.unet
    vae = pipe.vae

    vae.to(device)
    text_encoder.to(device)
    unet.to(device)

    vae.requires_grad_(False)
    text_encoder.requires_grad_(False)
    vae.eval()
    text_encoder.eval()

    if hasattr(unet, "enable_gradient_checkpointing"):
        unet.enable_gradient_checkpointing()
        logger.info("Gradient checkpointing enabled")

    lora_config = LoraConfig(
        r=args.rank,
        lora_alpha=args.rank,
        init_lora_weights="gaussian",
        target_modules=["to_k", "to_q", "to_v", "to_out.0"],
    )
    unet = get_peft_model(unet, lora_config)
    trainable = sum(p.numel() for p in unet.parameters() if p.requires_grad)
    total = sum(p.numel() for p in unet.parameters())
    logger.info(f"LoRA params: {trainable:,} trainable / {total:,} total ({100*trainable/total:.2f}%)")

    noise_scheduler = pipe.scheduler

    class VisemeDataset(Dataset):
        def __init__(self, entries, dataset_dir, resolution):
            self.entries = entries
            self.dataset_dir = dataset_dir
            self.resolution = resolution

        def __len__(self):
            return len(self.entries)

        def __getitem__(self, idx):
            entry = self.entries[idx]
            img_path = self.dataset_dir / entry["file_name"]
            image = Image.open(img_path).convert("RGB").resize(
                (self.resolution, self.resolution), Image.Resampling.LANCZOS
            )
            transform = T.Compose([
                T.ToTensor(),
                T.Normalize([0.5], [0.5]),
            ])
            pixel_values = transform(image)
            return {"pixel_values": pixel_values, "text": entry["text"]}

    dataset = VisemeDataset(entries, dataset_dir, args.resolution)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    optimizer = torch.optim.AdamW(
        [p for p in unet.parameters() if p.requires_grad],
        lr=args.lr,
        weight_decay=1e-2,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    total_batches = len(dataloader)
    logger.info(f"Training for {args.epochs} epochs, lr={args.lr}, rank={args.rank}")
    logger.info(f"Batch size={args.batch_size}, grad accum={args.gradient_accumulation}, batches/epoch={total_batches}")

    global_step = 0
    for epoch in range(1, args.epochs + 1):
        unet.train()
        epoch_loss = 0.0
        num_batches = 0

        for batch_idx, batch in enumerate(dataloader):
            pixel_values = batch["pixel_values"].to(device, dtype=dtype)
            captions = batch["text"]

            with torch.no_grad():
                tokens = tokenizer(
                    captions,
                    max_length=tokenizer.model_max_length,
                    padding="max_length",
                    truncation=True,
                    return_tensors="pt",
                )
                encoder_hidden_states = text_encoder(tokens.input_ids.to(device))[0]
                latents = vae.encode(pixel_values).latent_dist.sample() * vae.config.scaling_factor

            noise = torch.randn_like(latents)
            timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps,
                                      (latents.shape[0],), device=device).long()
            noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)

            noise_pred = unet(noisy_latents, timesteps, encoder_hidden_states).sample
            loss = torch.nn.functional.mse_loss(noise_pred, noise)

            loss = loss / args.gradient_accumulation
            loss.backward()

            if (batch_idx + 1) % args.gradient_accumulation == 0:
                torch.nn.utils.clip_grad_norm_(unet.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad()
                global_step += 1

            epoch_loss += loss.item() * args.gradient_accumulation
            num_batches += 1

            if batch_idx % 10 == 0:
                logger.info(f"  Epoch {epoch} batch {batch_idx+1}/{total_batches} loss={loss.item()*args.gradient_accumulation:.6f}")

        avg_loss = epoch_loss / max(num_batches, 1)
        logger.info(f"Epoch {epoch}/{args.epochs} — loss: {avg_loss:.6f} — steps: {global_step}")
        sys.stdout.flush()

        if epoch % args.save_every == 0 or epoch == args.epochs:
            ckpt_dir = output_dir / f"checkpoint-{epoch}"
            unet.save_pretrained(ckpt_dir)
            logger.info(f"Saved checkpoint to {ckpt_dir}")

    final_dir = output_dir / "final"
    unet.save_pretrained(final_dir)
    logger.info(f"Training complete. Final LoRA weights: {final_dir}")

    del unet, vae, text_encoder, pipe
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()

    print(f"\nTo use these weights, set in .env:")
    print(f"  CUSTOM_LOCAL_LORA_DIR={final_dir}")
    print(f"  CUSTOM_LOCAL_LORA_SCALE=0.8")


if __name__ == "__main__":
    main()
