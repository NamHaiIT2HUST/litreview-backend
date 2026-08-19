import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import re
from datetime import datetime
from pydantic import BaseModel, Field

# Add project root to sys.path so 'src' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.rag_service import rag_service, MIN_RELEVANCE_SCORE, MAX_CONTEXT_CHUNKS
from src.services.vector_store import vector_store_service
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class LLMJudgeResult(BaseModel):
    score: int = Field(description="Score from 0 to 10")
    reasoning: str = Field(description="Reasoning for the score")

class RefusalJudgeResult(BaseModel):
    declined_or_flagged: bool = Field(
        description="True if the answer correctly avoids fabricating an answer "
        "(e.g. says the documents don't cover this, or flags the false premise)."
    )
    reasoning: str = Field(description="Short reasoning for the verdict")

def clean_source_name(source_path):
    source_path = source_path.replace("\\", "/")
    basename = os.path.basename(source_path)
    uuid_prefix = re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_(.+)$",
        basename,
        re.IGNORECASE,
    )
    if uuid_prefix:
        return uuid_prefix.group(1)
    return basename

async def judge_synthesis(question, expected_points, actual_answer):
    prompt = PromptTemplate(
        template="""You are an expert evaluator grading an answer to a synthesis question based on a technical document.
Question: {question}

Expected Key Points:
{expected_points}

Actual Answer:
{actual_answer}

Rate how well the Actual Answer covers the Expected Key Points on a scale from 0 to 10.
0 = completely missed all points or incorrect.
10 = covered all points perfectly and accurately.

Provide a JSON output matching this schema:
{{
  "score": <int 0-10>,
  "reasoning": "<short string>"
}}
""",
        input_variables=["question", "expected_points", "actual_answer"],
    )
    
    try:
        chain = prompt | rag_service.llm | JsonOutputParser(pydantic_object=LLMJudgeResult)
        res = await chain.ainvoke({
            "question": question,
            "expected_points": "\n".join(f"- {p}" for p in expected_points),
            "actual_answer": actual_answer
        })
        return res.get("score", 0)
    except Exception as e:
        logger.error(f"Error calling LLM judge: {e}")
        return 0

async def judge_refusal(question, actual_answer):
    """For unanswerable/false-premise questions: does the answer correctly avoid
    fabricating a response, instead of hallucinating a confident-sounding answer?"""
    prompt = PromptTemplate(
        template="""You are grading whether a RAG system correctly handled a question that
CANNOT be answered from its source documents (either the documents don't cover the topic,
or the question contains a false premise not supported by the documents).

Question (unanswerable / false premise): {question}

System's Actual Answer: {actual_answer}

A CORRECT answer explicitly says the documents don't contain this information, or flags
that the premise doesn't match the source material. An INCORRECT answer confidently states
a fact as if it were supported by the documents (hallucination), even with hedging language.

Provide a JSON output matching this schema:
{{
  "declined_or_flagged": <true|false>,
  "reasoning": "<short string>"
}}
""",
        input_variables=["question", "actual_answer"],
    )
    try:
        chain = prompt | rag_service.llm | JsonOutputParser(pydantic_object=RefusalJudgeResult)
        res = await chain.ainvoke({"question": question, "actual_answer": actual_answer})
        return bool(res.get("declined_or_flagged", False))
    except Exception as e:
        logger.error(f"Error calling refusal judge: {e}")
        return False

async def run_benchmark(test_set_path: str):
    with open(test_set_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    os.makedirs("benchmark/results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file_path = f"benchmark/results/benchmark_{timestamp}.csv"
    
    results = []
    
    for idx, item in enumerate(test_data):
        logger.info(f"Processing question {idx+1}/{len(test_data)}: {item['id']}")
        try:
            q_id = item["id"]
            question = item["question"]
            expected_answer_contains = item["expected_answer_contains"]
            expected_source_file = item["expected_source_file"]
            expected_source_page = item["expected_source_page"]
            if expected_source_page is None:
                expected_source_pages = []
            elif isinstance(expected_source_page, int):
                expected_source_pages = [str(expected_source_page)]
            else:
                expected_source_pages = [str(p) for p in expected_source_page]
            q_type = item["type"]
            is_unanswerable = q_type == "unanswerable"
            
            # 1. Retrieval
            chunks = await vector_store_service.search_similar_documents(question, top_k=20)
            
            # Check retrieval recall
            retrieved_pages = set()
            for doc in chunks:
                source = clean_source_name(doc.metadata.get("source", ""))
                page = str(doc.metadata.get("page", ""))
                page_display = str(int(page) + 1) if page.isdigit() else page
                if source == expected_source_file:
                    retrieved_pages.add(page_display)
            
            pages_found = sum(1 for p in expected_source_pages if p in retrieved_pages)
            retrieval_recall = pages_found / len(expected_source_pages) if expected_source_pages else 0
            
            # 2. Generation with citations
            rag_res = await rag_service.generate_answer_with_citations(question, chunks)
            answer = rag_res["answer"]
            citations = rag_res["citations"]
            
            # 3. Answer Accuracy
            answer_lower = answer.lower()
            keywords_found = sum(1 for k in expected_answer_contains if k.lower() in answer_lower)
            answer_accuracy = keywords_found / len(expected_answer_contains) if expected_answer_contains else 0
            
            # 4. LLM Judge for Synthesis
            llm_score = 0
            if q_type == "synthesis":
                llm_score = await judge_synthesis(question, expected_answer_contains, answer)
            
            # 5. Citation Precision
            total_citations = 0
            valid_citations = 0
            for cit in citations:
                if cit.get("cited_in_answer"):
                    total_citations += 1
                    cit_page = str(cit.get("page", ""))
                    cit_source = clean_source_name(cit.get("filename", ""))
                    if cit_source == expected_source_file and cit_page in expected_source_pages:
                        valid_citations += 1
            
            citation_precision = valid_citations / total_citations if total_citations > 0 else 0

            # 6. Refusal correctness for unanswerable / false-premise questions
            refusal_correct = ""
            if is_unanswerable:
                refusal_correct = 1 if await judge_refusal(question, answer) else 0

            results.append({
                "id": q_id,
                "type": q_type,
                "retrieval_recall": retrieval_recall,
                "answer_accuracy": answer_accuracy,
                "citation_precision": citation_precision,
                "llm_score": llm_score,
                "refusal_correct": refusal_correct,
                "total_citations": total_citations,
                "error": ""
            })

        except Exception as e:
            logger.error(f"Error processing {item['id']}: {e}")
            results.append({
                "id": item["id"],
                "type": item["type"],
                "retrieval_recall": 0,
                "answer_accuracy": 0,
                "citation_precision": 0,
                "llm_score": 0,
                "refusal_correct": "",
                "total_citations": 0,
                "error": str(e)
            })

    # Summary
    metrics_by_type = {
        "factual": {"count": 0, "recall": 0, "acc": 0, "prec": 0, "llm": 0},
        "synthesis": {"count": 0, "recall": 0, "acc": 0, "prec": 0, "llm": 0},
        "unanswerable": {"count": 0, "refusal": 0},
    }

    with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "type", "retrieval_recall", "answer_accuracy", "citation_precision", "llm_score", "refusal_correct", "total_citations", "error"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # Write config metadata row
        writer.writerow({
            "id": "CONFIG",
            "type": "META",
            "error": f"MIN_RELEVANCE_SCORE={MIN_RELEVANCE_SCORE}, MAX_CONTEXT_CHUNKS={MAX_CONTEXT_CHUNKS}"
        })

        for r in results:
            writer.writerow(r)
            t = r["type"]
            metrics_by_type.setdefault(t, {"count": 0, "recall": 0, "acc": 0, "prec": 0, "llm": 0})
            metrics_by_type[t]["count"] += 1
            if t == "unanswerable":
                metrics_by_type[t]["refusal"] = metrics_by_type[t].get("refusal", 0) + (r["refusal_correct"] or 0)
            else:
                metrics_by_type[t]["recall"] += r["retrieval_recall"]
                metrics_by_type[t]["acc"] += r["answer_accuracy"]
                metrics_by_type[t]["prec"] += r["citation_precision"]
                metrics_by_type[t]["llm"] += r.get("llm_score", 0)

    print("\n" + "="*50)
    print("BENCHMARK SUMMARY")
    print("="*50)
    for t in ["factual", "synthesis"]:
        count = metrics_by_type[t]["count"]
        if count == 0:
            continue
        print(f"--- {t.upper()} ({count} questions) ---")
        print(f"Retrieval Recall:   {metrics_by_type[t]['recall'] / count * 100:.2f}%")
        print(f"Answer Accuracy:    {metrics_by_type[t]['acc'] / count * 100:.2f}% (keyword match)")
        print(f"Citation Precision: {metrics_by_type[t]['prec'] / count * 100:.2f}%")
        if t == "synthesis":
            print(f"LLM Judge Score:    {metrics_by_type[t]['llm'] / count:.2f}/10")

    unans_count = metrics_by_type["unanswerable"]["count"]
    if unans_count > 0:
        print(f"--- UNANSWERABLE ({unans_count} questions) ---")
        print(f"Correctly declined/flagged: {metrics_by_type['unanswerable']['refusal'] / unans_count * 100:.2f}%")

    print(f"\nDetailed results saved to: {csv_file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG benchmark harness.")
    parser.add_argument("--test-set", type=str, required=True, help="Path to test set JSON file")
    args = parser.parse_args()
    
    asyncio.run(run_benchmark(args.test_set))
