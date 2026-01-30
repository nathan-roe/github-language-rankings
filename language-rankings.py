from __future__ import annotations

import os
import requests
from typing import Optional
import base64
import matplotlib.pyplot as plt

user =  os.environ.get("GITHUB_USER", "")
token = os.environ.get("GITHUB_TOKEN", "")

url = f"https://api.github.com/users/{user}/repos"

headers = {
    "Accept": "application/vnd.github+json",
    **({"Authorization": f"Bearer {token}"} if token else {}),
}


def get_language_aggregate() -> dict:
    response = requests.get(url=url, headers=headers)
    response.raise_for_status()

    language_aggregate = {}
    repos = response.json()
    for r in repos:
        if "languages_url" in r:
            response = requests.get(url=r["languages_url"], headers=headers)
            response.raise_for_status()

            lang_map = response.json()
            for k, v in lang_map.items():
                language_aggregate[k] = (language_aggregate[k] if k in language_aggregate else 0) + v
    return language_aggregate


def _strip_inline_comment(s: str) -> str:
    """
    Remove inline comments that start with #, but only when # is not inside quotes.
    """
    in_single = False
    in_double = False
    for i, ch in enumerate(s):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return s[:i].rstrip()
    return s.rstrip()


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s


def parse_language_type_and_color(yml_text: str) -> dict[str, dict[str, Optional[str]]]:
    """
    Returns: {language_name: {"type": <str|None>, "color": <str|None>}, ...}
    """
    languages: dict[str, dict[str, Optional[str]]] = {}

    current_lang: Optional[str] = None

    for raw_line in yml_text.splitlines():
        line = raw_line.rstrip("\n")

        # Skip YAML document marker and empty lines
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue

        # Skip full-line comments (allow leading spaces)
        if stripped.startswith("#"):
            continue

        # Top-level key: "Language Name:"
        if line and not line[0].isspace() and stripped.endswith(":"):
            lang_name = stripped[:-1].strip()
            current_lang = lang_name
            languages.setdefault(current_lang, {"type": None, "color": None})
            continue

        # If we're not inside a language block, ignore
        if current_lang is None:
            continue

        # We only care about fields at indentation level 2: "  type: ..." / "  color: ..."
        if line.startswith("  ") and not line.startswith("    "):
            no_comment = _strip_inline_comment(line.strip())
            if ":" not in no_comment:
                continue

            key, value = no_comment.split(":", 1)
            key = key.strip()
            value = _unquote(value.strip()) if value.strip() else ""

            if key == "type":
                languages[current_lang]["type"] = value or None
            elif key == "color":
                languages[current_lang]["color"] = value or None

    return languages


def get_language_colors(yml_file_data: str) -> dict[str, str | None]:
    parsed = parse_language_type_and_color(yml_file_data)

    out: dict[str, Optional[str]] = {}
    for lang_name, attrs in parsed.items():
        if attrs.get("type") != "programming":
            continue

        color = attrs.get("color")
        if color is None:
            continue

        out[lang_name] = color
    return out


def _top_languages_with_other(language_aggregate: dict[str, int], top_k: int = 8) -> tuple[list[str], list[int]]:
    items = sorted(language_aggregate.items(), key=lambda kv: kv[1], reverse=True)
    if len(items) <= top_k:
        labels = [k for k, _ in items]
        sizes = [v for _, v in items]
        return labels, sizes

    top = items[:top_k]
    rest = items[top_k:]
    labels = [k for k, _ in top] + ["Other"]
    sizes = [v for _, v in top] + [sum(v for _, v in rest)]
    return labels, sizes

def generate_chart_file(profile: dict[str, str], language_aggregate: dict[str, int], color_map: dict[str, str]) -> None:
    plt.style.use("seaborn-v0_8-white")
    labels, sizes = _top_languages_with_other(language_aggregate, top_k=8)

    total = float(sum(sizes)) if sizes else 1.0
    percents = [s / total * 100.0 for s in sizes]

    # Use GitHub Linguist colors where possible; fall back to palette
    fallback_cmap = plt.get_cmap("tab20")
    colors = []
    for i, lang in enumerate(labels):
        c = color_map.get(lang)
        colors.append(c if c else fallback_cmap(i % fallback_cmap.N))

    fig, ax = plt.subplots(figsize=(9, 6), facecolor="white")
    ax.set_facecolor("white")

    wedges, _ = ax.pie(
        sizes,
        labels=None,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2),
    )

    ax.axis("equal")

    ax.text(
        0,
        0.02,
        f"{profile['name'] if profile and 'name' in profile else user}",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="semibold",
        color="#111827",
    )
    ax.text(
        0,
        -0.10,
        "Most Used Languages",
        ha="center",
        va="center",
        fontsize=10,
        color="#6B7280",
    )

    legend_labels = [f"{lang} — {pct:.1f}%" for lang, pct in zip(labels, percents)]
    ax.legend(
        wedges,
        legend_labels,
        title="",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        fontsize=10,
        labelspacing=0.9,
        handlelength=1.2,
        handletextpad=0.6,
    )

    plt.tight_layout()
    plt.savefig("visualization.png", dpi=200, bbox_inches="tight")

if __name__ == "__main__":
    linguist_yml = requests.get(
        url="https://api.github.com/repos/github-linguist/linguist/contents/lib/linguist/languages.yml",
        headers=headers,
    )
    linguist_yml.raise_for_status()

    profile_response = requests.get(
        url=f'https://api.github.com/users/{user}',
        headers=headers,
    )
    profile_response.raise_for_status()

    color_map = get_language_colors(base64.b64decode(linguist_yml.json()["content"]).decode("utf-8"))
    language_aggregate = get_language_aggregate()

    generate_chart_file(profile_response.json(), language_aggregate, color_map)