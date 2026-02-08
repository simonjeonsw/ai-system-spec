"""Validation utilities for claim-to-source traceability."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Set


_SOURCE_ID_PATTERN = re.compile(r"src-\d+", re.IGNORECASE)


@dataclass
class VerificationResult:
    status: str
    errors: List[str]
    sentence_map: List[Dict[str, List[str]]]


def _extract_source_ids(text: str) -> Set[str]:
    return {match.lower() for match in _SOURCE_ID_PATTERN.findall(text or "")}


def _split_sentences(script_text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", script_text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _is_low_risk(sentence: str) -> bool:
    return bool(
        re.search(r"\b(in my opinion|i think|we believe|welcome|thanks for watching)\b", sentence, re.IGNORECASE)
        or re.search(r"\b(let's dive in|stick around|coming up next)\b", sentence, re.IGNORECASE)
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


class ScriptValidator:
    def __init__(self, research_payload: dict, script_payload: dict) -> None:
        self.research_payload = research_payload
        self.script_payload = script_payload
        self.source_ids = {
            source.get("source_id", "").lower()
            for source in research_payload.get("sources", [])
            if source.get("source_id")
        }

    def validate(self) -> VerificationResult:
        script_text = self.script_payload.get("script", "")
        citations = self.script_payload.get("citations", [])
        sentences = _split_sentences(script_text)
        citation_ids = _extract_source_ids(" ".join(citations)) if citations else set()

        errors: List[str] = []
        sentence_map: List[Dict[str, List[str]]] = []

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
            sentence_map.append(
                {
                    "sentence": sentence,
                    "sources": normalized_sources,
                    "risk_level": risk,
                    "requires_source": requires_source,
                }
            )

            if risk == "high" and not normalized_sources:
                errors.append(f"Sentence {index} high-risk claim missing verified source_id.")
            if risk == "medium" and requires_source and not normalized_sources:
                errors.append(f"Sentence {index} medium-risk claim missing verified source_id.")

        status = "pass" if not errors else "fail"
        return VerificationResult(status=status, errors=errors, sentence_map=sentence_map)
