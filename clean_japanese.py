#!/usr/bin/env python3
"""Normalize the exported Anki JSON decks for Japanese search and study."""

from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent / "forest-bloom-web" / "public" / "data" / "japanese"
LEVELS = ("N1", "N2", "N3", "N4", "N5")
VOCAB_BOOKS = ("redbook", "greenbook")
POS_SEPARATOR = re.compile(r"[•·・･、，,／/|＋+#\s]+")
FURIGANA_RE = re.compile(r"([一-龯々〆ヵヶ]+)[\[［]([ぁ-ゖァ-ヺー]+)[\]］]")
TERM_RE = re.compile(r"^\s*(.*?)\s*[\[［]([^\]］]+)[\]］]\s*$")
SOUND_RE = re.compile(r"\[sound:[^\]]*]", re.IGNORECASE)

POS_MAP = {
    "名": "名词", "名詞": "名词", "名词": "名词",
    "動": "动词", "動詞": "动词", "動詞1": "动词", "動詞2": "动词",
    "動詞3": "动词", "自動": "动词", "他動": "动词", "自動詞": "动词",
    "他動詞": "动词", "自他動": "动词", "自他動3": "动词",
    "自他": "动词", "自动": "动词", "他动": "动词", "自他动": "动词",
    "イ形": "い形容词", "い形容詞": "い形容词", "い形容词": "い形容词",
    "ナ形": "な形容词", "形": "形容词", "形動": "な形容词", "形动": "な形容词", "形容動": "な形容词", "形容動詞": "な形容词",
    "な形容詞": "な形容词", "形容詞": "形容词", "形容词": "形容词",
    "副": "副词", "副詞": "副词", "副词": "副词",
    "連体": "连体词", "連体詞": "连体词", "连体词": "连体词",
    "接続": "接续词", "接続詞": "接续词", "接续词": "接续词",
    "感動": "感叹词", "感動詞": "感叹词", "感叹词": "感叹词",
    "助詞": "助词", "助词": "助词", "助動詞": "助动词", "助动词": "助动词",
    "接頭": "接头词", "接頭詞": "接头词", "接头词": "接头词",
    "接尾": "接尾词", "接尾詞": "接尾词", "接尾词": "接尾词",
    "代名詞": "代词", "代词": "代词", "数詞": "数词", "数词": "数词",
    "連語": "词组", "惯用语": "惯用语", "慣用句": "惯用语",
}


class TextParser(HTMLParser):
    BLOCKS = {
        "address", "article", "blockquote", "dd", "div", "dl", "dt", "h1",
        "h2", "h3", "h4", "h5", "h6", "li", "ol", "p", "pre", "section",
        "table", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored += 1
        elif not self.ignored and (tag in self.BLOCKS or tag == "br"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored:
            self.ignored -= 1
        elif not self.ignored and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    parser = TextParser()
    parser.feed(SOUND_RE.sub("", value))
    text = html.unescape("".join(parser.parts))
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = value.strip()
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def split_term(value: str) -> tuple[str, str]:
    match = TERM_RE.match(value)
    if not match:
        return value.strip(), ""
    return match.group(1).strip(), match.group(2).strip()


def strip_leading_pos(value: str) -> tuple[list[str], str]:
    text = value.strip()
    tags: list[str] = []
    while True:
        match = re.match(r"^\s*[\[［]([^\]］]{1,30})[\]］]\s*", text)
        if not match:
            break
        tags.extend(POS_SEPARATOR.split(match.group(1)))
        text = text[match.end():]
    return unique(tags), text.strip()


def normalize_pos(raw_values: list[str]) -> tuple[list[str], list[str]]:
    raw: list[str] = []
    normalized: list[str] = []
    for value in raw_values:
        for token in POS_SEPARATOR.split(value.strip("[]［］()（） ")):
            token = token.strip()
            if not token:
                continue
            raw.append(token)
            candidate = re.sub(r"\d+$", "", token)
            label = POS_MAP.get(token) or POS_MAP.get(candidate)
            if label is None and candidate in {"自他", "自他動"}:
                label = "动词"
            if label is None and candidate in {"一类", "二类", "三类", "五段", "一段", "サ変", "カ変"}:
                continue
            if label is None:
                label = "其他"
            normalized.append(label)
    return unique(normalized), unique(raw)


def to_hiragana(value: str) -> str:
    result = []
    for char in value:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)
    return "".join(result)


def search_texts(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if not value:
            continue
        result.append(value)
        result.extend(match.group(2) for match in FURIGANA_RE.finditer(value))
        result.append(FURIGANA_RE.sub(r"\1", value))
        result.extend(to_hiragana(match.group(2)) for match in FURIGANA_RE.finditer(value))
        result.append(to_hiragana(value))
    return unique(result)


def kana_search_texts(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(match.group(2) for match in FURIGANA_RE.finditer(value))
        if not re.search(r"[一-龯々]", value) and re.search(r"[ぁ-ゖァ-ヺ]", value):
            result.append(value)
            result.append(to_hiragana(value))
    return unique(result)


def normalize_vocab(record: dict[str, Any], book: str, level: str) -> dict[str, Any] | None:
    raw_term = clean_text(record.get("Expression") if book == "redbook" else record.get("日文"))
    if not raw_term:
        return None
    headword, reading = split_term(raw_term)

    if book == "redbook":
        raw_meaning = clean_text(record.get("中文释义"))
        raw_pos, meaning = strip_leading_pos(raw_meaning)
        pos, raw_pos = normalize_pos(raw_pos)
        example = clean_text(record.get("例句"))
        related = clean_text(record.get("惯用/関係"))
        homophones = clean_text(record.get("同音"))
        pitch = clean_text(record.get("声调"))
    else:
        raw_pos, _ = strip_leading_pos(clean_text(record.get("词性")))
        if not raw_pos:
            raw_pos = [clean_text(record.get("词性"))]
        pos, raw_pos = normalize_pos(raw_pos)
        meaning = clean_text(record.get("释义"))
        example = ""
        related = ""
        homophones = ""
        pitch = clean_text(record.get("音调"))

    if not pos:
        pos = ["未标注"]

    examples = [{"text": example}] if example else []
    related_terms = [line for line in related.splitlines() if line.strip()]
    japanese_source = unique([headword, reading, *related_terms, *homophones.splitlines()])
    source_id = str(record.get("__guid__", ""))
    stable_id = str(record.get("__created_at__") or source_id)
    return {
        "id": f"{book}-{level.lower()}-{stable_id}",
        "sourceId": source_id,
        "book": book,
        "level": level,
        "kind": "vocabulary",
        "term": headword,
        "reading": reading,
        "writtenForms": unique([headword]),
        "partOfSpeech": pos,
        "sourcePartOfSpeech": raw_pos,
        "meaningZh": meaning,
        "pitchAccent": pitch,
        "examples": examples,
        "relatedTerms": related_terms,
        "homophones": [line for line in homophones.splitlines() if line.strip()],
        "search": {
            "meaningZh": unique([meaning, *related_terms]),
            "kana": kana_search_texts([reading, *japanese_source]),
            "written": search_texts(japanese_source),
        },
    }


def numbered_values(record: dict[str, Any], prefix: str, count: int) -> list[str]:
    return unique([
        clean_text(record.get(f"{prefix}{index}"))
        for index in range(1, count + 1)
        if clean_text(record.get(f"{prefix}{index}"))
    ])


def normalize_grammar(record: dict[str, Any], level: str) -> dict[str, Any] | None:
    term = clean_text(record.get("Word"))
    if not term:
        return None
    connections = numbered_values(record, "ConnectiveType", 10)
    explanations = numbered_values(record, "Explain", 15)
    notes = numbered_values(record, "Note", 15)
    examples = []
    for index in range(1, 26):
        japanese = clean_text(record.get(f"Example{index}"))
        chinese = clean_text(record.get(f"Chinese{index}"))
        tag = clean_text(record.get(f"SentenceTag{index}"))
        if japanese or chinese:
            examples.append({"ja": japanese, "zh": chinese, "tag": tag})

    japanese_content = [term, *connections, *(item["ja"] for item in examples)]
    chinese_content = [*explanations, *notes, *(item["zh"] for item in examples)]
    reading_parts = [reading for text in japanese_content for reading in
                     (match.group(2) for match in FURIGANA_RE.finditer(text))]
    source_id = str(record.get("Note ID") or record.get("__guid__", ""))
    stable_id = str(record.get("__created_at__") or source_id)
    return {
        "id": f"bluebook-{level.lower()}-{stable_id}",
        "sourceId": source_id,
        "book": "bluebook",
        "level": level,
        "kind": "grammar",
        "term": term,
        "reading": "",
        "writtenForms": unique([term]),
        "partOfSpeech": ["语法"],
        "sourcePartOfSpeech": [],
        "meaningZh": "\n".join(explanations),
        "connections": connections,
        "explanations": explanations,
        "examples": examples,
        "notes": notes,
        "search": {
            "meaningZh": unique(chinese_content),
            "kana": kana_search_texts(reading_parts + japanese_content),
            "written": search_texts(japanese_content),
        },
    }


def load_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} must contain a JSON array of objects.")
    return payload


def clean_decks(root: Path) -> tuple[int, list[str]]:
    output_root = root / "cleaned"
    total = 0
    reports: list[str] = []
    for book in VOCAB_BOOKS:
        for level in LEVELS:
            source = root / book / f"{level}cards.json"
            records = load_records(source)
            cleaned = [
                item for record in records
                if (item := normalize_vocab(record, book, level)) is not None
            ]
            write_deck(output_root / book / f"{level}.json", cleaned)
            total += len(cleaned)
            reports.append(f"{book}/{level}: {len(cleaned)}")

    for level in LEVELS:
        source = root / "bluebook" / "grammar" / f"{level}cards.json"
        records = load_records(source)
        cleaned = [
            item for record in records
            if (item := normalize_grammar(record, level)) is not None
        ]
        ids = [item["id"] for item in cleaned]
        if len(set(ids)) != len(ids):
            duplicates = sorted({item for item in ids if ids.count(item) > 1})
            raise ValueError(f"Duplicate grammar IDs in {source}: {duplicates[:5]}")
        write_deck(output_root / "bluebook" / f"{level}.json", cleaned)
        total += len(cleaned)
        reports.append(f"bluebook/{level}: {len(cleaned)}")
    return total, reports


def write_deck(path: Path, records: list[dict[str, Any]]) -> None:
    ids = [record["id"] for record in records]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicate IDs in output {path}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean the bundled Japanese Anki JSON exports.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Raw Japanese JSON directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total, reports = clean_decks(args.root.resolve())
    print("\n".join(reports))
    print(f"Generated {total} cleaned records under {args.root.resolve() / 'cleaned'}.")


if __name__ == "__main__":
    main()
