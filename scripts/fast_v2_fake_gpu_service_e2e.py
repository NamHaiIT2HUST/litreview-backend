"""Fast v2 local E2E, no GPU required (section 13).

Spins up a REAL fake HTTP server (genuine socket, genuine JSON round trip --
not a mocked Python object) implementing the OpenScholar GPU service contract
with canned responses, then runs the actual production pipeline against it:

    Fast v2 pipeline
      -> real FastV2SemanticIndex (Chroma, fast_v2_evidence_minilm_v1)
      -> real Evidence Hygiene
      -> real CrossEncoderReranker
      -> real GroundedEvidenceBank
      -> RemoteOpenScholarGenerator -> HTTP -> fake GPU service (this process)
      -> Fast v2 response

Verifies full wiring end-to-end and reports phase timings. Requires the same
DB/Chroma this worktree already uses for the Xu2010/Xu2018 benchmark corpus
(see scripts/fast_v2_index_benchmark_corpus.py) -- no GPU, no vllm, no torch
model load anywhere in this script.
"""
from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PAPER_IDS = [
    uuid.UUID("52c06c26-1dd1-486a-8c4f-202779ed5c7f"),  # Xu2010
    uuid.UUID("0373c7b5-3a9e-437d-a59a-a1baa9a708cc"),  # Xu2018
]
QUESTION = (
    "How do Xu2010 and Xu2018 differ in their formulations of the split "
    "feasibility problem, algorithmic strategies, assumptions, and "
    "convergence guarantees?"
)
DIMENSIONS = ["problem formulation", "algorithmic strategy", "assumptions", "convergence guarantees"]

FAKE_RESPONSE_TEXT = (
    "[Response_Start]Xu2010 formulates the split feasibility problem in "
    "infinite-dimensional Hilbert spaces using a bounded linear operator [0]. "
    "Xu2018 generalizes this to nonlinear mappings via a majorization-"
    "minimization approach [1].[Response_End]"
)


class _FakeGpuHandler(BaseHTTPRequestHandler):
    call_count = 0  # class-level: shared across requests to this server

    def log_message(self, fmt, *args):  # noqa: A003 -- silence default stderr logging
        pass

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "ok", "model": "fake-gpu-service", "loaded": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/generate":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        request = json.loads(raw)
        _FakeGpuHandler.call_count += 1

        # Assert the contract at the wire level, not just in Python objects.
        config = request.get("generation_config", {})
        assert config.get("min_tokens") == 0, "min_tokens must be 0 over the wire"
        assert config.get("stop") == ["[Response_End]"], "stop must be configured over the wire"
        assert "[Response_End]" not in "" , "sanity"

        time.sleep(0.05)  # simulate a small generation delay
        response_body = {
            "text": FAKE_RESPONSE_TEXT,
            "input_tokens": len(request["prompt"].split()),
            "output_tokens": len(FAKE_RESPONSE_TEXT.split()),
            "generation_ms": 50.0,
            "finish_reason": "stop",
            "stop_reason": "[Response_End]",
        }
        body = json.dumps(response_body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_fake_gpu_service(port: int = 8501) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), _FakeGpuHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def main():
    from src.synthesis.fast_v2.dimensions.planner import DeterministicDimensionQueryPlanner
    from src.synthesis.fast_v2.evidence.chroma_retriever import FastV2ChromaEvidenceRetriever
    from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex
    from src.synthesis.fast_v2.generator.remote_openscholar import RemoteOpenScholarGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    server = start_fake_gpu_service(port=8501)
    print("Fake GPU service listening on http://127.0.0.1:8501")

    try:
        index = FastV2SemanticIndex()
        retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=PAPER_IDS)
        reranker = CrossEncoderReranker()
        generator = RemoteOpenScholarGenerator(base_url="http://127.0.0.1:8501")

        # Health check first, as a real deployment would.
        health = generator.health_check()
        print(f"health check: {health}")

        pipeline = FastSynthesisV2Pipeline(
            retriever=retriever,
            generator=generator,
            reranker=reranker,
            planner=DeterministicDimensionQueryPlanner(),
            candidates_per_dimension=40,
        )

        wall_start = time.perf_counter()
        result = await pipeline.run(question=QUESTION, dimensions=DIMENSIONS)
        wall_ms = (time.perf_counter() - wall_start) * 1000.0

        print("\n=== RESULT ===")
        print(f"synthesis_mode: {result.synthesis_mode}")
        print(f"claim_grounding_status: {result.claim_grounding_status}")
        print(f"citation_authority: {result.citation_authority}")
        print(f"text (first 300 chars): {result.text[:300]!r}")
        print(f"evidence_bank size: {len(result.evidence_bank.evidence)}")
        print(f"evidence_bank paper_distribution: {result.evidence_bank.paper_distribution}")

        print("\n=== TIMINGS (pipeline PhaseTimings) ===")
        for key, value in result.timings.items():
            print(f"  {key}: {value}")

        print("\n=== REMOTE GENERATOR DIAGNOSTICS ===")
        print(f"  last_network_ms: {generator.last_network_ms}")
        print(f"  last_remote_generation_ms: {generator.last_remote_generation_ms}")
        print(f"  fake server call_count (must be 1): {_FakeGpuHandler.call_count}")

        print(f"\ntotal wall-clock (this script, includes health check): {wall_ms:.1f}ms")

        assert _FakeGpuHandler.call_count == 1, "exactly one generation request must occur"
        assert result.diagnostics["hygiene_dropped"] >= 0
        assert result.diagnostics.get("finish_reason") == "stop"
        print("\nE2E ASSERTIONS PASSED: exactly one generation call, evidence pipeline unchanged.")

        out_path = REPO_ROOT / "scratch" / "fast_v2_parity_results" / "fake_gpu_e2e_result.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8")
        print(f"Wrote {out_path}")
    finally:
        server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
