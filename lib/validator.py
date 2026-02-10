"""Validation utilities for claim-to-source traceability and semantic consistency."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Set


_SOURCE_ID_PATTERN = re.compile(r"src-\d+", re.IGNORECASE)
_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z\-']+")
_STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "have", "your", "into", "their", "about", "will",
    "they", "were", "there", "what", "when", "where", "which", "while", "then", "than", "them", "been",
    "over", "under", "very", "more", "most", "also", "only", "just", "some", "such", "through", "across",
    "because", "these", "those", "would", "could", "should", "being", "make", "made", "using", "used", "use",
    "into", "onto", "within", "without", "between", "each", "every", "other", "many", "much", "still", "even",
    "video", "today", "let", "lets", "here", "our", "you", "we", "it", "its", "is", "are", "was", "were",
}
_FINANCE_ANCHORS = {
    "inflation", "exchange", "rate", "rates", "currency", "cash", "savings", "bank", "fdic", "cpi",
    "purchasing", "power", "yield", "interest", "investment", "portfolio", "bond", "stocks", "wealth",
}
_NEURO_ANCHORS = {
    "brain", "neuron", "neurons", "neuroscience", "neuroplasticity", "hippocampus", "amygdala", "dopamine",
    "serotonin", "cortex", "synapse", "cognitive", "memory",
}


@dataclass
class VerificationResult:
    status: str
    errors: List[str]
    sentence_map: List[Dict[str, Any]]
    coverage: Dict[str, float]
    semantic: Dict[str, Any]


def _extract_source_ids(text: str) -> Set[str]:
    return {match.lower() for match in _SOURCE_ID_PATTERN.findall(text or "")}


def _normalize_script_text(script_text: str | List[str]) -> str:
    if isinstance(script_text, list):
        return "\n".join(str(item) for item in script_text)
    return str(script_text)


def _split_sentences(script_text: str | List[str]) -> List[str]:
    normalized = _normalize_script_text(script_text).strip()
    if not normalized:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _is_low_risk(sentence: str) -> bool:
    return bool(
        re.search(r"\b(in my opinion|i think|we believe|welcome|thanks for watching)\b", sentence, re.IGNORECASE)
        or re.search(r"\b(let's dive in|stick around|coming up next)\b", sentence, re.IGNORECASE)
    )


def _is_narrative(sentence: str) -> bool:
    return bool(
        re.search(
            r"\b(welcome back|today we're|let's explore|in this video|"
            r"here's the takeaway|stay tuned|subscribe)\b",
            sentence,
            re.IGNORECASE,
        )
    )


def _is_high_risk(sentence: str) -> bool:
    return bool(
        re.search(
            r"\b(invest|investment|stock|bond|crypto|etf|portfolio|interest rate|"
            r"tax|regulation|legal|lawsuit|compliance|inflation|gdp|cpi|fed|"
            r"central bank|recession|yield|earnings|balance sheet)\b",
            sentence,
            re.IGNORECASE,
        )
        or re.search(r"\$\d", sentence)
        or re.search(r"\b\d+(\.\d+)?%?\b", sentence)
    )


def _requires_source(sentence: str) -> bool:
    return bool(
        re.search(r"\b(according to|report|data|study|survey|estimate)\b", sentence, re.IGNORECASE)
        or re.search(r"\b\d{4}\b", sentence)
        or re.search(r"\d", sentence)
    )


def _risk_level(sentence: str) -> str:
    if _is_low_risk(sentence):
        return "low"
    if _is_high_risk(sentence):
        return "high"
    return "medium"


def _tokenize_keywords(text: str) -> List[str]:
    tokens = [w.lower() for w in _WORD_PATTERN.findall(text or "")]
    return [t for t in tokens if t not in _STOPWORDS and len(t) >= 4]


def _top_keywords(text: str, limit: int = 25) -> Set[str]:
    counts = Counter(_tokenize_keywords(text))
    return {token for token, _ in counts.most_common(limit)}


class ScriptValidator:
    def __init__(self, research_payload: dict, script_payload: dict) -> None:
        self.research_payload = research_payload
        self.script_payload = script_payload
        self.source_ids = {
            source.get("source_id", "").lower()
            for source in research_payload.get("sources", [])
            if source.get("source_id")
        }

    def _semantic_topic_alignment(self, script_text: str) -> List[str]:
        research_text = " ".join(
            [
                str(self.research_payload.get("executive_summary", "")),
                " ".join(str(x) for x in self.research_payload.get("key_facts", [])),
                str(self.research_payload.get("viewer_takeaway", "")),
            ]
        )
        research_keywords = _top_keywords(research_text)
        script_keywords = _top_keywords(script_text)
        overlap = research_keywords.intersection(script_keywords)

        errors: List[str] = []
        finance_in_research = bool(research_keywords.intersection(_FINANCE_ANCHORS))
        finance_in_script = bool(script_keywords.intersection(_FINANCE_ANCHORS))
        neuro_in_script = bool(script_keywords.intersection(_NEURO_ANCHORS))

        if finance_in_research and not finance_in_script:
            errors.append("CRITICAL: Topic alignment failure. Finance anchors missing in script.")
        if finance_in_research and neuro_in_script and len(overlap) < 3:
            errors.append("CRITICAL: Topic mismatch detected (research=finance, script=non-finance domain).")
        if len(overlap) < 3:
            errors.append(
                "CRITICAL: Semantic overlap too low between research and script keywords "
                f"(overlap={len(overlap)})."
            )
        return errors

    def semantic_consistency_check(
        self,
        *,
        metadata_payload: Dict[str, Any] | None = None,
        scene_output: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        script_text = _normalize_script_text(self.script_payload.get("script", ""))
        errors = self._semantic_topic_alignment(script_text)

        if metadata_payload:
            chapters = metadata_payload.get("chapters", [])
            script_keywords = _top_keywords(script_text, limit=80)
            for idx, chapter in enumerate(chapters, start=1):
                chapter_title = str(chapter.get("title", ""))
                chapter_tokens = set(_tokenize_keywords(chapter_title))
                chapter_tokens = {token for token in chapter_tokens if token not in {"chapter", "intro", "outro"}}
                if chapter_tokens and not (chapter_tokens.intersection(script_keywords)):
                    errors.append(
                        f"CRITICAL: Metadata chapter {idx} not represented in script content: '{chapter_title}'."
                    )

            estimated_runtime_sec = metadata_payload.get("estimated_runtime_sec")
            if estimated_runtime_sec is None:
                words = len(script_text.split())
                estimated_runtime_sec = int((words / 230) * 60)
            scenes = (scene_output or {}).get("scenes", [])
            if estimated_runtime_sec > 300 and len(scenes) < 10:
                errors.append(
                    "CRITICAL: Granularity check failed. Long-form script (>5 min) must produce at least 10 scenes. "
                    f"current_scenes={len(scenes)}"
                )

        return {
            "status": "pass" if not errors else "fail",
            "errors": errors,
        }

    def validate(self) -> VerificationResult:
        script_text = self.script_payload.get("script", "")
        citations = self.script_payload.get("citations", [])
        sentences = _split_sentences(script_text)
        citation_ids = _extract_source_ids(" ".join(citations)) if citations else set()

        errors: List[str] = []
        sentence_map: List[Dict[str, Any]] = []
        factual_total = 0
        factual_cited = 0
        section_total = {"high": 0, "medium": 0}
        section_cited = {"high": 0, "medium": 0}

        for index, sentence in enumerate(sentences, start=1):
            sentence_sources = _extract_source_ids(sentence)
            if not sentence_sources and citations:
                if len(citations) == len(sentences):
                    sentence_sources = _extract_source_ids(citations[index - 1])
                else:
                    sentence_sources = citation_ids

            normalized_sources = sorted({src for src in sentence_sources if src in self.source_ids})
            risk = _risk_level(sentence)
            requires_source = _requires_source(sentence)
            is_narrative = _is_narrative(sentence)
            sentence_map.append(
                {
                    "sentence": sentence,
                    "sources": normalized_sources,
                    "risk_level": risk,
                    "requires_source": requires_source,
                    "is_narrative": is_narrative,
                }
            )

            if is_narrative or risk == "low":
                continue
            if requires_source:
                factual_total += 1
                if risk in section_total:
                    section_total[risk] += 1
                if normalized_sources:
                    factual_cited += 1
                    if risk in section_cited:
                        section_cited[risk] += 1
            if risk == "high" and not normalized_sources:
                errors.append(f"Sentence {index} high-risk claim missing verified source_id.")
            if risk == "medium" and requires_source and not normalized_sources:
                errors.append(f"Sentence {index} medium-risk claim missing verified source_id.")

        if factual_total > 0:
            ratio = factual_cited / factual_total
            if ratio >= 0.5:
                errors = [err for err in errors if "medium-risk" not in err]

        semantic = self.semantic_consistency_check()
        errors.extend(semantic["errors"])

        status = "pass" if not errors else "fail"
        coverage = {
            "factual_coverage": round((factual_cited / factual_total), 4) if factual_total else 0.0,
            "high_risk_coverage": round((section_cited["high"] / section_total["high"]), 4) if section_total["high"] else 0.0,
            "medium_risk_coverage": round((section_cited["medium"] / section_total["medium"]), 4) if section_total["medium"] else 0.0,
        }
        return VerificationResult(
            status=status,
            errors=errors,
            sentence_map=sentence_map,
            coverage=coverage,
            semantic=semantic,
        )
