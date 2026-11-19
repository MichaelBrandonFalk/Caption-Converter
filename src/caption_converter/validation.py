"""Inspect original source lines before the legacy parsers split cue payloads.

Valid files pass through unchanged. Repairs only remove misplaced separator
lines or replace an unambiguous embedded header; normalization remains in core.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


_SRT_TIME = r"\d{2,}:[0-5]\d:[0-5]\d,\d{3}"
_VTT_TIME = r"(?:\d{1,}:)?[0-5]\d:[0-5]\d(?:\.\d{1,3})?"
_TIMINGS = {
    fmt: re.compile(rf"^\s*({time})\s+-->\s+({time})(?:[ \t]+.*)?\s*$")
    for fmt, time in (("srt", _SRT_TIME), ("vtt", _VTT_TIME))
}
_EMBEDDED_SRT = re.compile(rf"^\s*({_SRT_TIME})\s+-->\s+({_SRT_TIME})\s*$")
_SUSPECT_TIMING = re.compile(r"^\s*\d+:\d{2}.*(?:--(?:>|&gt;)|->)")


class CaptionParseError(ValueError):
    """Source dialogue needs review; conversion must not write partial outputs."""


@dataclass
class _Header:
    line: int
    first: int
    identifier: str | None
    start: float
    end: float


def _seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    seconds, _, fraction = parts[-1].partition(".")
    # Match the existing parser's handling of short VTT decimal fields.
    return (int(parts[-3]) * 3600 if len(parts) == 3 else 0) + int(parts[-2]) * 60 + int(seconds) + int(fraction or "0") / 1000


def prepare_caption_content(content: str, fmt: str) -> str:
    lines = content.splitlines()
    if not lines:
        return content
    lines[0] = lines[0].lstrip("\ufeff")
    ignored: set[int] = set()
    if fmt == "vtt":
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if i == 0 and line.startswith("WEBVTT"):
                ignored.add(i)
                i += 1
                while i < len(lines) and lines[i].startswith("X-TIMESTAMP-MAP="):
                    ignored.add(i)
                    i += 1
            elif (
                (i == 0 or not lines[i - 1].strip())
                and re.match(r"^(?:NOTE(?:\s|$)|STYLE$|REGION$)", line)
            ):
                while i < len(lines) and lines[i].strip():
                    ignored.add(i)
                    i += 1
            else:
                i += 1

    headers: list[_Header] = []

    def review(reason: str, line: int, header: _Header | None, text: list[str]) -> None:
        cue = (f"cue {header.identifier}" if header.identifier else f"cue at line {header.line + 1}") if header else "unowned text"
        raise CaptionParseError(
            f"Review required ({cue}, source line {line + 1}): {reason}. "
            "No outputs written; original file unchanged.\nText to review:\n" + "\n".join(text)
        )

    for i, raw in enumerate(lines):
        if i in ignored:
            continue
        match = _TIMINGS[fmt].fullmatch(raw)
        if not match:
            continue
        first = i
        identifier = None
        if i > 0 and lines[i - 1].strip() and i - 1 not in ignored:
            previous = lines[i - 1].strip()
            if (i == 1 or not lines[i - 2].strip()) and (
                previous.isdigit() if fmt == "srt" else "-->" not in previous
            ):
                first = i - 1
                identifier = previous
            else:
                review("timing line has no clear cue boundary", i, None, lines[max(0, i - 1):i + 2])
        headers.append(_Header(i, first, identifier, _seconds(match[1]), _seconds(match[2])))

    prefix_end = headers[0].first if headers else len(lines)
    for i in range(prefix_end):
        if i not in ignored and lines[i].strip():
            review("dialogue has no valid timing header", i, None, lines[i:prefix_end])

    removed: set[int] = set()
    changed = False
    for index, header in enumerate(headers):
        previous = headers[index - 1] if index else None
        following = headers[index + 1] if index + 1 < len(headers) else None
        stop = following.first if following else len(lines)
        payload = [i for i in range(header.line + 1, stop) if i not in ignored and lines[i].strip()]

        if fmt == "vtt":
            embedded = [i for i in payload if _TIMINGS["srt"].fullmatch(lines[i].replace("&gt;", ">"))]
            if embedded:
                i = embedded[0]
                match = _TIMINGS["srt"].fullmatch(lines[i].replace("&gt;", ">"))
                assert match is not None
                start, end = _seconds(match[1]), _seconds(match[2])
                safe = (
                    len(embedded) == 1 and len(payload) >= 3 and i == payload[1]
                    and _EMBEDDED_SRT.fullmatch(lines[i].replace("&gt;", ">")) is not None
                    and payload[1] == payload[0] + 1
                    and header.identifier is not None and header.identifier.isdigit()
                    and lines[payload[0]].strip() == header.identifier
                    and header.end <= header.start
                    and previous is not None and following is not None
                    and previous.start < previous.end <= start
                    and header.start <= start < end <= following.start < following.end
                )
                if not safe:
                    review("embedded SRT header cannot be safely assigned within surrounding cue times", i, header, [lines[j] for j in payload])
                lines[header.line] = f"{match[1].replace(',', '.')} --> {match[2].replace(',', '.')}"
                header.start, header.end = start, end
                removed.update(payload[:2])
                payload = payload[2:]
                changed = True

        for i in payload:
            if _SUSPECT_TIMING.match(lines[i]):
                review("unrecognized or misplaced timing header", i, header, [lines[j] for j in payload])

        # A blank before or within dialogue would make the legacy parser lose it.
        # A trailing blank is the normal cue delimiter and is left alone.
        blanks = [i for i in range(header.line + 1, payload[-1] if payload else header.line + 1)
                  if i not in ignored and i not in removed and not lines[i].strip()]
        if blanks:
            numbered = (header.identifier is not None and following is not None
                        and following.identifier is not None and header.identifier.isdigit()
                        and following.identifier.isdigit()
                        and int(following.identifier) == int(header.identifier) + 1)
            ordered = following is not None and header.start <= header.end <= following.start
            if not (following is not None and ((fmt == "srt" and numbered) or (fmt == "vtt" and ordered))):
                review("detached dialogue has ambiguous cue ownership", blanks[0], header, [lines[j] for j in payload])
            removed.update(blanks)
            changed = True

    if not changed:
        return content
    repaired = "\n".join(line for i, line in enumerate(lines) if i not in removed)
    return repaired + ("\n" if content.endswith(("\n", "\r")) else "")
