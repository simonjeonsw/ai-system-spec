"""Validation utilities for claim-to-source traceability and semantic consistency."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Set


_SOURCE_ID_PATTERN = re.compile(r"src-\d+", re.IGNORECASE)
_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z\-']+")
_STAGE_TAG_PATTERN = re.compile(r"\[(?:visual|narration|scene)\s*:[^\]]*\]|\[(?:visual|narration|scene)\]", re.IGNORECASE)
_PART_MARKER_PATTERN = re.compile(r"---\s*PART\s*\d+\s*:[^-]+---", re.IGNORECASE)
_STRUCTURAL_ONLY_PATTERN = re.compile(r"^(?:\*+|\d+\.|\[src-\d+\]|[-–—\s]+)$", re.IGNORECASE)
_DIRECTIVE_PREFIX_PATTERN = re.compile(r"^(opening shot|title card|graph|animation|overlay|host appears|secondary graph|chart|infographic)\s*:", re.IGNORECASE)
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
    coverage: Dict[str, float | bool]
    semantic: Dict[str, Any]


def _extract_source_ids(text: str) -> Set[str]:
    return {match.lower() for match in _SOURCE_ID_PATTERN.findall(text or "")}


def _normalize_script_text(script_text: str | List[str]) -> str:
    if isinstance(script_text, list):
        return "\n".join(str(item) for item in script_text)
    return str(script_text)


def _clean_validation_text(text: str) -> str:
    cleaned = _STAGE_TAG_PATTERN.sub(" ", text or "")
    cleaned = _PART_MARKER_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"\[visual:[^\]]*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace('\\"', '"')
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_structural_fragment(sentence: str) -> bool:
    stripped = sentence.strip()
    if not stripped:
        return True
    if _STRUCTURAL_ONLY_PATTERN.match(stripped):
        return True
    if _DIRECTIVE_PREFIX_PATTERN.match(stripped):
        return True
    if len(stripped) <= 3 and re.match(r"^\d+\.?$", stripped):
        return True
    return False


def _split_sentences(script_text: str | List[str]) -> List[str]:
    normalized = _normalize_script_text(script_text).strip()
    if not normalized:
        return []
    cleaned = _clean_validation_text(normalized)
    raw_sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    normalized_sentences: List[str] = []
    for sentence in raw_sentences:
        cleaned_sentence = re.sub(r"^[\s:;,.\-–—]+", "", sentence.strip())
        if cleaned_sentence and not _is_structural_fragment(cleaned_sentence):
            normalized_sentences.append(cleaned_sentence)
    return normalized_sentences


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
            r"central bank|recession|yield|earnings|balance sheet|wage|productivity|poverty)\b",
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


def _sources_per_claim_stats(sentence_map: List[Dict[str, Any]]) -> Dict[str, float | bool]:
    high_risk_claims = [entry for entry in sentence_map if entry.get("risk_level") == "high"]
    if not high_risk_claims:
        return {"avg_sources_per_high_risk_claim": 0.0, "over_assignment_risk": False}

    avg_sources = sum(len(entry.get("sources", [])) for entry in high_risk_claims) / len(high_risk_claims)
    over_assignment_risk = avg_sources > 2.2 and len(high_risk_claims) >= 4
    return {
        "avg_sources_per_high_risk_claim": round(avg_sources, 4),
        "over_assignment_risk": over_assignment_risk,
    }


def _tokenize_keywords(text: str) -> List[str]:
    tokens = [w.lower() for w in _WORD_PATTERN.findall(text or "")]
    return [t for t in tokens if t not in _STOPWORDS and len(t) >= 4]


def _top_keywords(text: str, limit: int = 25) -> Set[str]:
    counts = Counter(_tokenize_keywords(text))
    return {token for token, _ in counts.most_common(limit)}


def _script_semantic_corpus(script_payload: Dict[str, Any]) -> str:
    script = script_payload.get("script", "")
    if isinstance(script, dict):
        sections = script.get("sections", [])
        chunks: list[str] = [str(script.get("title", ""))]
        for section in sections if isinstance(sections, list) else []:
            chunks.append(str(section.get("title", "")))
            narration = section.get("narration", "")
            if isinstance(narration, list):
                chunks.extend(str(n) for n in narration)
            else:
                chunks.append(str(narration))
            chunks.append(str(section.get("visual", "")))
        return " ".join(chunks)
    return _normalize_script_text(script)


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
        script_text = _script_semantic_corpus(self.script_payload)
        errors = self._semantic_topic_alignment(script_text)

        if metadata_payload:
            chapters = metadata_payload.get("chapters", [])
            script_tokens = set(_tokenize_keywords(script_text))
            for idx, chapter in enumerate(chapters, start=1):
                chapter_title = str(chapter.get("title", ""))
                chapter_tokens = set(_tokenize_keywords(chapter_title))
                chapter_tokens = {token for token in chapter_tokens if token not in {"chapter", "intro", "outro"}}
                if chapter_tokens and len(chapter_tokens.intersection(script_tokens)) < 1:
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
        high_risk_source_ids: list[str] = []

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
            if risk == "high":
                high_risk_source_ids.extend(normalized_sources)
                if not normalized_sources:
                    errors.append(f"Sentence {index} high-risk claim missing verified source_id.")
            if risk == "medium" and requires_source and not normalized_sources:
                errors.append(f"Sentence {index} medium-risk claim missing verified source_id.")

        if factual_total > 0:
            ratio = factual_cited / factual_total
            if ratio >= 0.5:
                errors = [err for err in errors if "medium-risk" not in err]

        semantic = self.semantic_consistency_check()
        errors.extend(semantic["errors"])

        high_risk_total = section_total["high"]
        unique_high_sources = set(high_risk_source_ids)
        source_diversity_score = round((len(unique_high_sources) / high_risk_total), 4) if high_risk_total else 0.0
        single_source_risk = bool(high_risk_total and len(unique_high_sources) <= 1)
        source_precision = _sources_per_claim_stats(sentence_map)
        if source_precision.get("over_assignment_risk"):
            errors.append("Source precision warning: high-risk claims appear over-assigned to too many sources.")

        status = "pass" if not errors else "fail"
        coverage: Dict[str, float | bool] = {
            "factual_coverage": round((factual_cited / factual_total), 4) if factual_total else 0.0,
            "high_risk_coverage": round((section_cited["high"] / section_total["high"]), 4) if section_total["high"] else 0.0,
            "medium_risk_coverage": round((section_cited["medium"] / section_total["medium"]), 4) if section_total["medium"] else 0.0,
            "source_diversity_score": source_diversity_score,
            "single_source_risk": single_source_risk,
            "avg_sources_per_high_risk_claim": source_precision.get("avg_sources_per_high_risk_claim", 0.0),
            "over_assignment_risk": source_precision.get("over_assignment_risk", False),
        }
        return VerificationResult(
            status=status,
            errors=errors,
            sentence_map=sentence_map,
            coverage=coverage,
            semantic=semantic,
        )
