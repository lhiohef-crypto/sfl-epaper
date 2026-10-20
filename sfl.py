import json
from pathlib import Path

import requests

URL = "https://sf.esports.capcom.com/api/sfl2026/?data=results"
PAGE = "https://sf.esports.capcom.com/sfl2026/schedule/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Referer": PAGE,
    "x-fd-mode": "retrieve_all",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


CACHE = Path(__file__).parent / "cache.json"


def fetch(offline=False):
    """APIから取得する。取得できなければ cache.json にフォールバックする。

    成功時は cache.json を最新データで更新するので、
    ネットワークが無い環境でも直前の結果で開発を続けられる。
    """
    if not offline:
        try:
            r = requests.get(URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()["data"]
            CACHE.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            return data
        except requests.RequestException as e:
            if not CACHE.exists():
                raise
            print(f"[warn] API取得に失敗 ({e.__class__.__name__})。"
                  f"cache.json を使用します")

    if not CACHE.exists():
        raise FileNotFoundError(CACHE)
    return json.loads(CACHE.read_text(encoding="utf-8"))


def latest_finished(schedules):
    """結果が入っている節のうち、最も日付が新しいものを返す"""
    done = []
    for s in schedules:
        sec = s["fields"]["section"]
        played = any(
            isinstance(sec.get(f"match{i}", {}).get("result"), dict)
            for i in range(1, 5)
        )
        if played:
            done.append((sec["time"], s))
    if not done:
        return None
    done.sort(key=lambda x: x[0])
    return done[-1][1]


def extract_matches(post, teams):
    sec = post["fields"]["section"]
    rows = []
    for i in range(1, 5):
        m = sec.get(f"match{i}")
        if not m or m.get("use") != "show":
            continue
        if not isinstance(m.get("result"), dict):
            continue
        pt = m["result"]["total"]["point"]
        rows.append({
            "no": i,
            "home": teams[m["home"]]["name"],
            "away": teams[m["away"]]["name"],
            "home_pt": pt["home"],
            "away_pt": pt["away"],
            "winner": m["result"]["winner"],
        })
    return rows


def standings(teams, division):
    rows = [t for t in teams.values() if t["division"] == division]
    rows.sort(
        key=lambda t: (t["point"], t["battle_diff"], t["round_diff"]),
        reverse=True,
    )
    return rows


def main():
    data = fetch()
    teams = data["teams"]

    post = latest_finished(data["schedules"])
    if post is None:
        print("結果のある節がありません")
        return

    sec = post["fields"]["section"]
    print(f'{post["post_title"]}   {sec["time"][:10]}')
    print("-" * 52)

    for m in extract_matches(post, teams):
        mark_h = "*" if m["winner"] == "home" else " "
        mark_a = "*" if m["winner"] == "away" else " "
        print(f'Match {m["no"]}  '
              f'{mark_a}{m["away"]:<26} {m["away_pt"]:>2}'
              f' - '
              f'{m["home_pt"]:>2} {m["home"]}{mark_h}')

    div = "s" if "Division S" in post["post_title"] else "f"
    print()
    print(f"Division {div.upper()} 順位表")
    print("-" * 52)
    for rank, t in enumerate(standings(teams, div), 1):
        print(f'{rank}. {t["name"]:<28} {t["point"]:>3}pt  '
              f'B{t["battle_diff"]:+d} R{t["round_diff"]:+d}')


if __name__ == "__main__":
    main()