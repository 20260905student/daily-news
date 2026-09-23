"""Create a Japanese, source-linked daily news digest from public RSS."""
import datetime as dt
import calendar
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests

ROOT = Path(__file__).parent
DATA = ROOT / "data"
PUBLIC = ROOT / "public"
JST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(JST)
TODAY = NOW.date()
SECTIONS = {
    "general": ("世間のニュース", "国内 国際 政治 経済 災害 重要ニュース"),
    "stocks": ("株式投資", "日経平均 TOPIX 米国株 S&P500 FRB 決算 金利"),
    "crypto": ("暗号資産", "ビットコイン イーサリアム 仮想通貨 ETF 規制"),
    "ai": ("AI", "生成AI OpenAI Google Anthropic 半導体 AI 最新"),
}


def collect(query):
    url = "https://news.google.com/rss/search?q=" + quote(query + " when:2d") + "&hl=ja&gl=JP&ceid=JP:ja"
    response = requests.get(url, timeout=20, headers={"User-Agent": "DailyNewsReader/1.0"})
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    items = []
    seen = set()
    cutoff = NOW - dt.timedelta(hours=48)
    for entry in feed.entries:
        title = re.sub(r"\s+-\s+[^-]+$", "", entry.get("title", "")).strip()
        link = entry.get("link", "")
        if not title or not link or title in seen or not link.startswith("https://"):
            continue
        stamp = entry.get("published_parsed")
        if not stamp:
            continue
        published = dt.datetime.fromtimestamp(calendar.timegm(stamp), dt.timezone.utc).astimezone(JST)
        if published < cutoff or published > NOW + dt.timedelta(minutes=5):
            continue
        seen.add(title)
        items.append({"title": title, "url": link, "source": entry.get("source", {}).get("title", "配信元"), "published": published.isoformat()})
        if len(items) == 14:
            break
    return items


def summarize(sections):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return sections, "要約用の設定が未完了のため、出典付き見出しを表示しています。"
    payload = {section: [{"title": item["title"], "source": item["source"]} for item in items] for section, items in sections.items()}
    prompt = ("次の日本語ニュース見出しのみを根拠として、4部門それぞれ重要度順に最大5件選び、"
              "各件に80字以内の日本語の要点を付けてください。見出しから確認できない数字・背景・影響は創作せず、"
              "投資助言はしないでください。JSONで {\"general\":[{\"index\":0,\"summary\":\"...\"}],"
              "\"stocks\":[],\"crypto\":[],\"ai\":[]} の形で返してください。"
              "indexは各部門の入力配列の0始まりの番号です。\n" + json.dumps(payload, ensure_ascii=False))
    try:
        result = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            params={"key": key}, timeout=70,
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}},
        )
        result.raise_for_status()
        parsed = json.loads(result.json()["candidates"][0]["content"]["parts"][0]["text"])
        output = {}
        for section, items in sections.items():
            selected = []
            used = set()
            for row in parsed.get(section, []):
                index = row.get("index")
                summary = row.get("summary")
                if type(index) is int and 0 <= index < len(items) and index not in used and isinstance(summary, str):
                    used.add(index)
                    selected.append({**items[index], "summary": summary[:160]})
                if len(selected) >= 5:
                    break
            output[section] = selected or items[:5]
        return output, None
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"Summary unavailable: {type(exc).__name__}")
        return {section: items[:5] for section, items in sections.items()}, "要約を取得できなかったため、出典付き見出しを表示しています。"


def render(edition, dates):
    def esc(value):
        return html.escape(str(value), quote=True)

    blocks = []
    for key, (label, _) in SECTIONS.items():
        cards = []
        for item in edition["sections"].get(key, []):
            cards.append(f'<article><a href="{esc(item["url"])}" target="_blank" rel="noopener noreferrer">{esc(item["title"])} <span aria-hidden="true">↗</span></a><p>{esc(item.get("summary", "見出しの詳細は出典をご確認ください。"))}</p><small>{esc(item["source"])} · {esc(item["published"][11:16])}</small></article>')
        blocks.append(f'<section id="{key}"><h2>{esc(label)}</h2>{"".join(cards) or "<p>該当する記事を取得できませんでした。</p>"}</section>')
    options = "".join(f'<option value="{esc(day)}" {"selected" if day == edition["date"] else ""}>{esc(day)}</option>' for day in dates)
    notice = f'<p class="notice">{esc(edition["notice"])}</p>' if edition.get("notice") else ""
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#10243b"><meta name="description" content="世間・日米株・暗号資産・AIのニュースを毎朝まとめるダッシュボード"><title>朝のニュース | {esc(edition["date"])}</title><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%2310243b'/%3E%3Ccircle cx='32' cy='34' r='15' fill='%23f2b65b'/%3E%3Cpath d='M14 48h36' stroke='white' stroke-width='4'/%3E%3C/svg%3E"><link rel="stylesheet" href="/daily-news/style.css"></head><body><header><div class="wrap head"><div><span class="eyebrow">DAILY BRIEF · JAPAN</span><h1>朝のニュース</h1><p>気になる4分野を、出典とともに。</p></div><div class="date"><label for="edition">発行日</label><select id="edition" onchange="location.href='/daily-news/archive/'+this.value+'.html'">{options}</select><small>更新: {esc(edition["updated_at"][:16].replace("T", " "))} JST</small></div></div></header><main class="wrap"><nav aria-label="分野"><a href="#general">世間</a><a href="#stocks">株式</a><a href="#crypto">暗号資産</a><a href="#ai">AI</a></nav>{notice}<div class="grid">{"".join(blocks)}</div><footer>記事の見出し・要点は配信時点の情報です。投資判断は元記事と一次情報をご確認ください。</footer></main></body></html>'''


def main():
    DATA.mkdir(exist_ok=True)
    PUBLIC.mkdir(exist_ok=True)
    collected = {}
    for section, (_, query) in SECTIONS.items():
        try:
            collected[section] = collect(query)
        except requests.RequestException as exc:
            print(f"Feed unavailable in {section}: {exc}")
            collected[section] = []
    if not any(collected.values()):
        raise RuntimeError("All news feeds failed; keep the existing edition instead")
    selected, notice = summarize(collected)
    edition = {"date": TODAY.isoformat(), "updated_at": NOW.isoformat(), "notice": notice, "sections": selected}
    (DATA / f"{TODAY}.json").write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
    cutoff = TODAY - dt.timedelta(days=29)
    for path in DATA.glob("????-??-??.json"):
        if dt.date.fromisoformat(path.stem) < cutoff:
            path.unlink()
    dates = sorted((p.stem for p in DATA.glob("????-??-??.json")), reverse=True)
    archive = PUBLIC / "archive"
    archive.mkdir(exist_ok=True)
    for old in archive.glob("*.html"):
        old.unlink()
    for day in dates:
        record = json.loads((DATA / f"{day}.json").read_text(encoding="utf-8"))
        page = render(record, dates)
        (archive / f"{day}.html").write_text(page, encoding="utf-8")
        if day == dates[0]:
            (PUBLIC / "index.html").write_text(page, encoding="utf-8")
    print(f"Built {len(dates)} editions, latest {dates[0]}")


if __name__ == "__main__":
    main()
