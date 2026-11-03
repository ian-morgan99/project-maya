"""tools/model_sweep.py - sweep LM Studio's model folder and report which models Strata can run.

Strata natively runs one architecture: Qwen3.8-Flash-Next ("qwen4exp").  Maya was built from Strata but
rewrote its engine for GLM-5.3-Flash and added DeepSeek-V4.1-Flash-1017 and MiniMax-M3.1-Flash engines of its own.
Strata itself does NOT run GLM, DeepSeek, or MiniMax.

This script scans every folder under LM Studio's model folder (models_root: $MAYA_LMSTUDIO_MODELS, else the
~/.lmstudio/models or ~/.cache/lm-studio/models this PC uses), identifies what each folder contains, and classifies
it as:
  - strata_qwen: Qwen3.8-Flash-Next architecture (Strata's native arch) - may run on Strata
  - maya_glm: GLM-5.3-Flash (Maya's engine only)
  - maya_deepseek: DeepSeek-V4.1-Flash-1017 (Maya's engine only)
  - maya_minimax: MiniMax-M3.1-Flash (Maya's engine only)
  - maya_qwen: CYBER-FROST-3.8-PS (Maya's Qwen path, not Strata's)
  - unsupported: different model/architecture entirely

Nothing is moved, deleted, or changed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

def models_root() -> Path:
    """LM Studio's model folder: $MAYA_LMSTUDIO_MODELS when set, else the first of its two locations that exists
    (~/.lmstudio/models, or ~/.cache/lm-studio/models before LM Studio 0.3), else the first candidate anyway (so the
    sweep reports an empty folder rather than failing on a PC without LM Studio)."""
    env = os.environ.get("MAYA_LMSTUDIO_MODELS")
    if env:
        return Path(env).expanduser().resolve()
    cands = [Path.home() / ".lmstudio" / "models", Path.home() / ".cache" / "lm-studio" / "models"]
    return next((c for c in cands if c.is_dir()), cands[0])


MODELS_ROOT = models_root()

# ------------------------------------------------------------------ what Strata natively runs
# Strata's engine is a native implementation of Qwen3.8-Flash-Next ("qwen4exp").
# Maya's Qwen support is CYBER-FROST-3.8-PS (Blackfrost-AI's fine-tune) on Maya's own Qwen path - not Strata's.
STRATA_ARCH = "qwen4exp"
STRATA_MODEL_NAMES = {
    "qwen3.8-flash-next", "qwen3.8-flash-next-gguf", "qwen3.8-flash-next-q4_k_xl",
    "qwen3.8-flash-next-q8_0", "qwen3.8-flash-next-iq1_s", "qwen3.8-flash-next-iq4_nl",
}

# ------------------------------------------------------------------ Maya's supported models (from maya.py MODELS, DS4_QUANTS, MM3_QUANTS, QWEN)
MAYA_MODELS = {
    # GLM-5.3-Flash (Maya's `maya` engine)
    "glm-5.3-flash": {
        "Maya-S-v2-IQ2_XXS", "Maya-S24", "Maya-XS-IQ1_S", "Maya-M", "Maya-M-Derisked", "Maya-L",
        "EXL3-3.05bpw", "EXL3-4.05bpw", "GLM-5.3-Flash-DFlash2",
    },
    # DeepSeek-V4.1-Flash-1017 (Maya's `maya-ds4` engine)
    "deepseek-v4.1-flash": {
        "UD-Q8_K_XL", "UD-Q4_K_XL", "UD-IQ1_S", "UD-IQ1_M", "UD-IQ2_XXS", "UD-Q2_K_XL",
        "UD-IQ3_XXS", "UD-IQ3_S", "UD-Q3_K_XL", "EXL3 2.9bpw", "EXL3 3.5bpw",
        "Mix-128G", "Mix-256G", "ista-iq2xxs",
    },
    # MiniMax-M3.1-Flash (Maya's `maya-mm3` engine)
    "minimax-m3.1-flash": {
        "Maya-XS", "Maya-S", "EXL3 3.5 bits",
    },
    # CYBER-FROST-3.8-PS (Maya's Qwen path)
    "cyber-frost-3.8-ps": {"q5_k_m"},
}

# ------------------------------------------------------------------ known model folders and what they contain
# (folder name -> (family, quant, notes))
KNOWN = {
    # verified 2026-11-03: packs with tools/mm3/pack_gguf.py (indexers present in all 60 layers) and runs on
    # maya-mm3 - configured as maya-minimax-ud-iq1_m.json.  Its first shard is 28 bytes short of the alignment its
    # own header asks for (it holds metadata only, no tensors), so it needs padding before packing.
    "unsloth/minimax-m3.1-flash-gguf": ("maya_minimax", "UD-IQ1_M",
                                        "packs and runs on maya-mm3 - configured as maya-minimax-ud-iq1_m.json; its "
                                        "first shard needs 28 bytes of alignment padding to pack"),
    "unsloth/Qwen3.8-2.4T-A95B-GGUF": ("unsupported", "Qwen3.8-2.4T-A95B", "Not a Maya or Strata model"),
    "unsloth/Qwen3.8-Flash-Next-GGUF": ("strata_qwen", "UD-IQ1_S", "Qwen3.8-Flash-Next - Strata's native arch, but unsloth's UD-IQ1_S layout may not match Strata's expected format"),
    "lmstudio-community/Muse-Glimmer-30B-GGUF": ("unsupported", "Muse-Glimmer-30B", "Not a Maya or Strata model"),
    "lmstudio-community/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-GGUF": ("unsupported", "Nemotron-3.5-Super-VL", "Not a Maya or Strata model"),
    "lmstudio-community/Qwen3.8-27B-GGUF": ("unsupported", "Qwen3.8-27B", "Not CYBER-FROST-3.8-PS; not Strata's qwen4exp"),
    "lmstudio-community/flint-GGUF": ("unsupported", "flint", "Not a Maya or Strata model"),
    "IndrasMirror/DeepSeek-V4.1-Flash-GSQ-Uncensored": ("unsupported", "DeepSeek-V4.1-Flash-GSQ-Uncensored", "Different layout from Maya's DeepSeek catalog"),
    "InsidiousFiddler/Kolibri-1-GGUF": ("unsupported", "Kolibri-1", "Not a Maya or Strata model"),
    "Maximilian228/Qwen3.8-Flash-Next-NVIDIA-NVFP4-Strata": ("unsupported", "Qwen3.8-Flash-Next-NVFP4", "NVFP4 quant - Maya doesn't support NVFP4 for Qwen"),
    "orcarouter/OrcaCyber-Nano-1.0": ("unsupported", "OrcaCyber-Nano-1.0", "Not Maya's orcarouter abliterated DeepSeek"),
    "pfeifferj/Qwen3.8-Flash-Next-GSQ-RCO-GGUF": ("strata_qwen", "GSQ-RCO companion", "Companion files only (mmproj + n-gram embeddings), no main model"),
    "prithivMLmods/Nanbeige4.3-33B-NVFP4-GGUF": ("unsupported", "Nanbeige4.3-33B", "Not a Maya or Strata model"),
    "prometheusAIR/DeepSeek-V4-Flash-Vision-Exp-GGUF": ("unsupported", "DeepSeek-V4-Flash-Vision-Exp", "DeepSeek V4 Flash, not V4.1-Flash-1017"),
    "recouper/Josiefied-Qwen3-8B-abliterated-v1-Q6_K-GGUF": ("unsupported", "Qwen3-8B", "Not Qwen3.8-Flash-Next CYBER-FROST"),
    "solstice-ai/DeepSeek-V4-Flash-Vision-Exp-NVFP4": ("unsupported", "DeepSeek-V4-Flash-Vision-Exp-NVFP4", "DSpark drafter + vision for DeepSeek-V4-Flash-Vision-Exp"),
    "incoai/Qwen3.8-27B-DFlash2-GGUF": ("unsupported", "Qwen3.8-27B-DFlash2", "Not a Maya model"),
    "anbeeld/GLM-5.3-Flash-DFlash2-GGUF": ("maya_glm", "DFlash2", "Maya's DFlash2 drafter - usable with --dflash for GLM"),
    # verified 2026-11-03: right architecture (glm5-next, 46 layers, 288 experts) but its tensors are named the
    # upstream llama.cpp way - kda_q/kda_v/kda_output - while Maya's engine and packer read attn_q/attn_v and
    # ssm_a/ssm_beta/ssm_f_a/ssm_conv1d_*.  tools/iq_pack.py refuses it fail-closed, so no pack can be built.
    "baekpica/GLM-5.3-Flash-Uncensored-Mixed-Quant-GGUF": (
        "unsupported", "GLM-5.3-Flash-Uncensored",
        "glm5-next but tensors named kda_* instead of the attn_*/ssm_* names Maya's engine reads - "
        "iq_pack.py refuses it fail-closed"),
    "huihui-ai/Huihui-MiniCPM-V-4_5-abliterated": ("unsupported", "MiniCPM-V-4_5", "Not a Maya or Strata model"),
    "huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF": ("strata_qwen", "UD-Q4_K_XL", "Qwen3.8-Flash-Next - Strata's native arch, but UD-Q4_K_XL layout may not match Strata's expected format"),
    "renketong/Huihui-Qwen3.8-27B-abliterated-NVFP4-GGUF": ("unsupported", "Qwen3.8-27B", "Not CYBER-FROST-3.8-PS"),
    "utautako/Qwen3.8-27B-NVFP4-MTP-Q8attn-GGUF": ("unsupported", "Qwen3.8-27B-NVFP4", "Not CYBER-FROST-3.8-PS"),
    "peasantsmith/GLM-5.3-Flash-Maya-GGUF": ("maya_glm", "Maya-S-v2-IQ2_XXS", "Already configured - Maya's GLM-5.3-Flash Maya-S"),
    "ista-daslab/deepseek-v4.1-flash-1017-gsq-rco-gguf": ("maya_deepseek", "ista-iq2xxs", "Already configured - Maya's DeepSeek ISTA GSQ-RCO"),
    "ista-daslab/qwen3.8-flash-next-gsq-rco-gguf": ("strata_qwen", "GSQ-RCO Q2_0", "Qwen3.8-Flash-Next GSQ-RCO - Strata's native arch, but GSQ-RCO layout may not match Strata's expected format"),
    "local-stress/Qwen3.8-27B-Q8_0": ("unsupported", "Qwen3.8-27B-Q8_0", "Symlink to lmstudio-community/Qwen3.8-27B-GGUF"),
}

# KNOWN is looked up by the lowercased folder path, but its keys are written as the folders are actually named.
# Map the lowercase form onto them so a mixed-case key still matches (without this every folder fell through to the
# name-guessing branch and reported quant "unknown").
_KNOWN_BY_LOWER = {k.lower(): v for k, v in KNOWN.items()}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(64 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files_under(folder: Path) -> list:
    """Every file under folder (links followed), each real file once."""
    seen, out = {}, []
    for root, dirs, names in os.walk(folder, followlinks=True):
        dirs.sort()
        for n in sorted(names):
            p = Path(root) / n
            if n.endswith((".incomplete", ".part", ".aria2", ".td", ".xltd", ".!ut", ".done")):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            if not p.is_file():
                continue
            key = (st.st_dev, st.st_ino) if st.st_ino else (str(p.resolve()),)
            if key in seen:
                continue
            seen[key] = len(out)
            out.append((p, p.resolve(), st.st_size))
    return out


def classify(folder: Path) -> dict:
    """Classify one model folder: family, quant, strata_support, files, size."""
    rel = folder.relative_to(MODELS_ROOT).as_posix()
    key = rel.lower()
    known = KNOWN.get(key) or _KNOWN_BY_LOWER.get(key)

    files = []
    total = 0
    for p, real, size in files_under(folder):
        if p.suffix.lower() in (".gguf", ".bin", ".json", ".txt", ".safetensors"):
            files.append({"name": p.name, "size": size, "path": str(p)})
            total += size

    ggufs = [f for f in files if f["name"].endswith(".gguf")]
    has_gguf = bool(ggufs)
    has_bin = any(f["name"].endswith(".bin") for f in files)
    has_safetensors = any(f["name"].endswith(".safetensors") for f in files)

    if known:
        family, quant, notes = known
    else:
        # Try to guess from file names
        names = " ".join(f["name"].lower() for f in files)
        if "qwen3.8-flash-next" in names:
            family, quant, notes = "strata_qwen", "unknown", "Qwen3.8-Flash-Next - Strata's native arch"
        elif "glm-5.3-flash" in names:
            family, quant, notes = "maya_glm", "unknown", "GLM-5.3-Flash - Maya's engine only"
        elif "deepseek-v4.1-flash" in names:
            family, quant, notes = "maya_deepseek", "unknown", "DeepSeek-V4.1-Flash-1017 - Maya's engine only"
        elif "minimax" in names:
            family, quant, notes = "maya_minimax", "unknown", "MiniMax-M3.1-Flash - Maya's engine only"
        elif "cyber-frost" in names:
            family, quant, notes = "maya_qwen", "unknown", "CYBER-FROST-3.8-PS - Maya's Qwen path"
        else:
            family, quant, notes = "unsupported", "unknown", "Not recognized as a Maya or Strata model"

    strata_support = family == "strata_qwen"
    maya_support = family in ("maya_glm", "maya_deepseek", "maya_minimax", "maya_qwen")

    return {
        "folder": rel,
        "family": family,
        "quant": quant,
        "notes": notes,
        "strata_support": strata_support,
        "maya_support": maya_support,
        "total_gb": round(total / 1e9, 2),
        "file_count": len(files),
        "gguf_count": len(ggufs),
        "has_gguf": has_gguf,
        "has_bin": has_bin,
        "has_safetensors": has_safetensors,
        "files": files[:20],  # first 20 for the report
    }


def sweep() -> dict:
    """Sweep all model folders and return a report."""
    results = []
    for d in sorted(MODELS_ROOT.iterdir()) if MODELS_ROOT.is_dir() else []:
        if not d.is_dir():
            continue
        for sub in sorted(d.iterdir()):
            if sub.is_dir():
                results.append(classify(sub))
    results.sort(key=lambda r: (r["family"], r["folder"]))
    return {
        "root": str(MODELS_ROOT),
        "total_folders": len(results),
        "strata_support": sum(1 for r in results if r["strata_support"]),
        "maya_support": sum(1 for r in results if r["maya_support"]),
        "unsupported": sum(1 for r in results if not r["strata_support"] and not r["maya_support"]),
        "total_gb": round(sum(r["total_gb"] for r in results), 2),
        "models": results,
    }


def main():
    report = sweep()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
