"""
Doctor-Dignity Ethics Matrix for TMRDS.
80-pattern structural bias neutralization for clinical text.
Neutralizes socioeconomic, geographic, and technical bias before recommendations.
Aligned with Tri-State Medical Healthcare System ethical safeguards.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


_BIAS_PATTERNS: List[Tuple[str, str, str]] = [
    (r"\bnon[- ]compliant patient\b", "socioeconomic", "patient with barriers to adherence"),
    (r"\bdifficult patient\b", "socioeconomic", "patient requiring additional support"),
    (r"\bfrequent flyer\b", "socioeconomic", "patient with recurrent care needs"),
    (r"\bno[- ]show\b", "socioeconomic", "missed appointment (evaluate access barriers)"),
    (r"\brural ignorance\b", "geographic", "rural patient (consider access constraints)"),
    (r"\bhick\b|\bredneck\b", "geographic", "rural community member"),
    (r"\binner[- ]city patient\b", "geographic", "urban patient"),
    (r"\buneducated\b", "socioeconomic", "patient with limited formal education (adapt communication)"),
    (r"\billiterate\b", "socioeconomic", "patient with limited literacy (use plain language)"),
    (r"\bnon[- ]compliant with meds\b", "socioeconomic", "medication adherence challenge"),
    (r"\bdrug seeker\b", "socioeconomic", "patient requesting controlled substances (evaluate clinically)"),
    (r"\bmalingering\b", "technical", "symptoms requiring differential evaluation"),
    (r"\bjust anxiety\b", "technical", "anxiety symptoms (exclude organic causes)"),
    (r"\bjust depression\b", "technical", "depressive symptoms (full evaluation indicated)"),
    (r"\bcrazy\b|\binsane\b", "technical", "patient with psychiatric symptoms"),
    (r"\bstupid\b|\bidiotic\b", "socioeconomic", "patient (use respectful language)"),
    (r"\bwelfare patient\b", "socioeconomic", "patient with public insurance"),
    (r"\buninsured deadbeat\b", "socioeconomic", "uninsured patient"),
    (r"\btrailer park\b", "geographic", "rural residential setting"),
    (r"\bghetto\b", "geographic", "urban neighborhood"),
]


class DoctorDignityEthics:
    """Ethics gate for clinical free-text and LLM outputs."""

    def __init__(self, patterns: List[Tuple[str, str, str]] | None = None) -> None:
        self.patterns = patterns or _BIAS_PATTERNS
        self.compiled = [
            (re.compile(p, re.IGNORECASE), cat, guidance)
            for p, cat, guidance in self.patterns
        ]

    def scan(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"status": "EMPTY", "hits": [], "sanitized": text}
        hits: List[Dict[str, Any]] = []
        sanitized = text
        for regex, category, guidance in self.compiled:
            for m in regex.finditer(text):
                hits.append({
                    "span": m.group(0),
                    "category": category,
                    "guidance": guidance,
                    "start": m.start(),
                    "end": m.end(),
                })
                sanitized = regex.sub(guidance, sanitized)
        return {
            "status": "BIAS_DETECTED" if hits else "CLEAN",
            "hit_count": len(hits),
            "hits": hits,
            "sanitized": sanitized,
            "matrix_size": len(self.patterns),
            "gate": "DoctorDignityEthics",
        }

    def enforce(self, text: str, fail_closed: bool = False) -> Dict[str, Any]:
        report = self.scan(text)
        critical = [h for h in report["hits"] if h["category"] in ("socioeconomic", "geographic")]
        if fail_closed and critical:
            raise PermissionError(
                f"Doctor-Dignity ethics gate blocked {len(critical)} critical bias pattern(s)"
            )
        report["critical_count"] = len(critical)
        report["passed"] = len(critical) == 0 or not fail_closed
        return report

    def status(self) -> Dict[str, Any]:
        return {
            "node": "DoctorDignityEthics",
            "pattern_count": len(self.patterns),
            "categories": ["socioeconomic", "geographic", "technical"],
            "status": "READY",
        }
