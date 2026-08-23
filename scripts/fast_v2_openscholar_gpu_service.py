"""Reference GPU service for NeuML/Llama-3.1_OpenScholar-8B-AWQ via vLLM.

Loads the model ONCE at process startup (module-level, before the ASGI app
starts serving) and keeps it warm in VRAM for the life of the process --
every request reuses the same engine. Deliberately lives outside
``src/synthesis/fast_v2`` and is never imported by the P-165 backend: this is
the GPU-only side of the split-process deployment that
``RemoteOpenScholarGenerator`` (in the backend) talks to over HTTP.

Contract (matches src/synthesis/fast_v2/generator/remote_openscholar.py):

    GET  /health   -> {"status": "ok", "model": "...", "loaded": true}
    POST /generate -> {"prompt": "...", "generation_config": {...}}
                    <- {"text": ..., "input_tokens": ..., "output_tokens": ...,
                        "generation_ms": ..., "finish_reason": ..., "stop_reason": ...}

Engine/generation settings are the exact validated Colab configuration
(see src/synthesis/fast_v2/generator/openscholar.py -- FROZEN_ENGINE_CONFIG /
FROZEN_GENERATION_CONFIG -- this script's defaults mirror those constants so
there is one place the numbers are recorded, but this script does not import
that module because it must stay CPU-import-safe for the backend and this
script is GPU-only from the first line).

Run (on a machine with an NVIDIA GPU -- T4/L4/A10 or better, vLLM installed):

    python scripts/fast_v2_openscholar_gpu_service.py --host 0.0.0.0 --port 8500

Or with uvicorn directly (model still loads once, at import time, either way):

    uvicorn scripts.fast_v2_openscholar_gpu_service:app --host 0.0.0.0 --port 8500

Colab: see the bottom of this file for a minimal cell-by-cell launch note.
"""
from __future__ import annotations

import argparse
import time
from typing import Any

MODEL_NAME = "NeuML/Llama-3.1_OpenScholar-8B-AWQ"

#: Mirrors src/synthesis/fast_v2/generator/openscholar.py::FROZEN_ENGINE_CONFIG.
#: Kept as a literal copy (not an import) so this module never imports
#: anything from src.synthesis.fast_v2 -- this file's first import already
#: requires a GPU, and the backend package must never accidentally import IT.
ENGINE_CONFIG: dict[str, Any] = {
    "quantization": "awq",
    "dtype": "float16",
    "max_model_len": 16384,
    "gpu_memory_utilization": 0.90,
    "enforce_eager": True,
    "disable_custom_all_reduce": True,
}

#: Server-side default generation config, overridden per-request by whatever
#: the client sends in "generation_config" (the client -- RemoteOpenScholarGenerator
#: -- always sends the frozen config explicitly; these are just safe fallbacks
#: if a field is omitted).
DEFAULT_GENERATION_CONFIG: dict[str, Any] = {
    "temperature": 0.7,
    "max_tokens": 3000,
    "min_tokens": 0,
    "stop": ["[Response_End]"],
    "stop_token_ids": [128009],
}


def _build_app():
    import torch
    import vllm
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    print(f"[fast_v2-gpu-service] loading {MODEL_NAME} (this happens ONCE)...")
    load_started = time.perf_counter()
    engine = vllm.LLM(
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
        tokenizer_mode="auto",
        tensor_parallel_size=torch.cuda.device_count(),
        **ENGINE_CONFIG,
    )
    load_seconds = time.perf_counter() - load_started
    print(f"[fast_v2-gpu-service] model loaded in {load_seconds:.1f}s -- staying warm")

    class GenerateRequest(BaseModel):
        prompt: str
        generation_config: dict[str, Any] = {}

    class GenerateResponse(BaseModel):
        text: str
        input_tokens: int | None = None
        output_tokens: int | None = None
        generation_ms: float
        finish_reason: str | None = None
        stop_reason: Any = None

    app = FastAPI(title="fast_v2 OpenScholar GPU service")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "model": MODEL_NAME, "loaded": True, "cold_load_seconds": round(load_seconds, 1)}

    @app.post("/generate", response_model=GenerateResponse)
    def generate(req: GenerateRequest) -> GenerateResponse:
        config = {**DEFAULT_GENERATION_CONFIG, **req.generation_config}
        if config.get("min_tokens"):
            raise HTTPException(
                status_code=400,
                detail="min_tokens must be 0 -- non-zero min_tokens caused the "
                "invalid 162.99s runaway-repetition run. Refusing to generate.",
            )

        sampling_params = vllm.SamplingParams(**config)

        started = time.perf_counter()
        outputs = engine.generate([req.prompt], sampling_params)
        generation_ms = (time.perf_counter() - started) * 1000.0

        completion = outputs[0].outputs[0]
        return GenerateResponse(
            text=completion.text,
            input_tokens=len(getattr(outputs[0], "prompt_token_ids", []) or []) or None,
            output_tokens=len(getattr(completion, "token_ids", []) or []) or None,
            generation_ms=generation_ms,
            finish_reason=getattr(completion, "finish_reason", None),
            stop_reason=getattr(completion, "stop_reason", None),
        )

    return app


# Module-level so `uvicorn scripts.fast_v2_openscholar_gpu_service:app` also
# loads the model exactly once, at import time.
app = None


def main() -> None:
    global app
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8500)
    args = parser.parse_args()

    import uvicorn

    app = _build_app()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
elif app is None:
    # Imported by `uvicorn scripts.fast_v2_openscholar_gpu_service:app`.
    app = _build_app()

# ---------------------------------------------------------------------------
# Colab launch note (no local GPU required on the P-165 dev machine):
#
#   !pip install vllm fastapi uvicorn
#   !python fast_v2_openscholar_gpu_service.py --host 0.0.0.0 --port 8500 &
#   # then expose :8500 (e.g. via ngrok / Colab's built-in port forwarding /
#   # a Cloudflare tunnel) and set on the P-165 backend:
#   #   FAST_V2_GENERATOR=remote_openscholar
#   #   FAST_V2_OPENSCHOLAR_BASE_URL=https://<the-forwarded-url>
# ---------------------------------------------------------------------------
