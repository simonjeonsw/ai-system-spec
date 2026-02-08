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


def _requires_source(sentence: str) -> bool:
    return bool(
        re.search(r"\d", sentence)
        or re.search(r"\b(percent|percentage|million|billion|trillion|cpi|gdp)\b", sentence, re.IGNORECASE)
        or re.search(r"\$\d", sentence)
    )


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
            sentence_map.append(
                {
                    "sentence": sentence,
                    "sources": normalized_sources,
                }
            )

            if _requires_source(sentence) and not normalized_sources:
                errors.append(f"Sentence {index} missing verified source_id.")

        status = "pass" if not errors else "fail"
        return VerificationResult(status=status, errors=errors, sentence_map=sentence_map)
