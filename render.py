from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import sfl

JST = timezone(timedelta(hours=9))

W, H = 400, 300
HEADER_H = 36
ROW_H = 84
LOGO = 66
FOOTER_Y = 288

BASE = Path(__file__).parent
LOGO_DIR = BASE / "logos"

F_BOLD = str(BASE / "NotoSansJP-Bold.ttf")
F_REG = str(BASE / "NotoSansJP-Regular.ttf")

WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ロゴの2値化方式
#   white  : 白背景に合成してそのまま2値化(濃い色のロゴ)
#   invert : 黒背景に合成して反転(白抜き・淡い色のロゴ)
#   alpha  : 透明でない部分をそのまま黒にする(細部の多い密なロゴ)
LOGO_MODE = {
    # dng は黒と白が同一ロゴ内に混在するため、white/invert では片方が消える
    "dng": "alpha",
}
# 勝者の見せ方: "badge"(黒地白抜き) / "underline"(下線) / "frame"(ロゴ枠) / "none"
WINNER_STYLE = "none"

LOGO_TH_DEFAULT = 150
LOGO_TH = {
    "varrel": 175,
    "cr": 130,
    "ixa": 130,
}


def font(path, size):
    return ImageFont.truetype(path, size)


def load_logo(key, size):
    """ロゴを読み込んで白黒2値に変換する(ディザなし・閾値方式)"""
    path = LOGO_DIR / f"{key}.png"
    if not path.exists():
        return None

    im = Image.open(path).convert("RGBA")
    mode = LOGO_MODE.get(key, "white")

    if mode == "alpha":
        gray = im.split()[3].point(lambda a: 0 if a > 128 else 255)
    else:
        bg_color = (0, 0, 0, 255) if mode == "invert" else (255, 255, 255, 255)
        bg = Image.new("RGBA", im.size, bg_color)
        gray = Image.alpha_composite(bg, im).convert("L")
        if mode == "invert":
            gray = ImageOps.invert(gray)

    gray.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("L", (size, size), 255)
    canvas.paste(gray, ((size - gray.width) // 2, (size - gray.height) // 2))

    th = LOGO_TH.get(key, LOGO_TH_DEFAULT)
    return canvas.point(lambda v: 255 if v > th else 0).convert("1")


def draw_score(d, x, y, text, f, anchor, win):
    """スコアを描く。勝者は WINNER_STYLE に従って強調する"""
    if win and WINNER_STYLE == "badge":
        l, t, r, b = d.textbbox((x, y), text, font=f, anchor=anchor)
        d.rectangle([l - 7, t - 4, r + 7, b + 4], fill=0)
        d.text((x, y), text, font=f, fill=1, anchor=anchor)
        return

    d.text((x, y), text, font=f, fill=0, anchor=anchor)

    if win and WINNER_STYLE == "underline":
        l, t, r, b = d.textbbox((x, y), text, font=f, anchor=anchor)
        d.rectangle([l - 2, b + 3, r + 2, b + 6], fill=0)


def render(post, matches):
    img = Image.new("1", (W, H), 1)
    d = ImageDraw.Draw(img)

    date = datetime.strptime(post["fields"]["section"]["time"][:10], "%Y-%m-%d")
    title = post["post_title"]

    d.rectangle([0, 0, W, HEADER_H], fill=0)
    d.text((10, HEADER_H // 2), date.strftime("%m/%d"),
           font=font(F_BOLD, 20), fill=1, anchor="lm")
    d.text((72, HEADER_H // 2 + 1), WD[date.weekday()],
           font=font(F_REG, 13), fill=1, anchor="lm")
    d.text((W - 10, HEADER_H // 2), title,
           font=font(F_BOLD, 16), fill=1, anchor="rm")

    for idx, m in enumerate(matches[:3]):
        top = HEADER_H + idx * ROW_H
        cy = top + ROW_H // 2

        for side, key, x in (("away", m["away_key"], 12),
                             ("home", m["home_key"], W - 12 - LOGO)):
            logo = load_logo(key, LOGO)
            if logo:
                img.paste(logo, (x, top + (ROW_H - LOGO) // 2))
                if WINNER_STYLE == "frame" and m.get("winner") == side:
                    ly = top + (ROW_H - LOGO) // 2
                    d.rectangle([x - 5, ly - 5, x + LOGO + 4, ly + LOGO + 4],
                                outline=0, width=2)
            else:
                d.rectangle([x, top + (ROW_H - LOGO) // 2,
                             x + LOGO, top + (ROW_H + LOGO) // 2], outline=0)

        d.text((W // 2, top + 20), f'Team Match {m["no"]}',
               font=font(F_REG, 12), fill=0, anchor="mm")

        f_big = font(F_BOLD, 32)
        sy = cy + 12
        d.text((W // 2, sy), "vs", font=font(F_REG, 14), fill=0, anchor="mm")
        for side, x, anchor in (("away", W // 2 - 34, "rm"),
                                ("home", W // 2 + 34, "lm")):
            win = (m.get("winner") == side)
            draw_score(d, x, sy, str(m[f"{side}_pt"]), f_big, anchor, win)

        if idx < 2:
            d.line([16, top + ROW_H, W - 16, top + ROW_H], fill=0)

    d.line([0, FOOTER_Y, W, FOOTER_Y], fill=0)
    d.text((W - 8, (FOOTER_Y + H) // 2),
           # Actions のランナーは UTC なので JST を明示する
           datetime.now(JST).strftime("updated %m/%d %H:%M"),
           font=font(F_REG, 10), fill=0, anchor="rm")

    return img


def main():
    data = sfl.fetch()

    post = sfl.latest_finished(data["schedules"])
    if post is None:
        print("結果のある節がありません")
        return

    matches = []
    sec = post["fields"]["section"]
    for i in range(1, 5):
        m = sec.get(f"match{i}")
        if not m or m.get("use") != "show":
            continue
        if not isinstance(m.get("result"), dict):
            continue
        pt = m["result"]["total"]["point"]
        matches.append({
            "no": i,
            "home_key": m["home"],
            "away_key": m["away"],
            "home_pt": pt["home"],
            "away_pt": pt["away"],
            "winner": m["result"]["winner"],
        })

    img = render(post, matches)
    img.save(BASE / "preview.png")
    img.resize((W * 2, H * 2), Image.NEAREST).save(BASE / "preview_2x.png")

    # Pico 用の生1bppバッファ (400x300 = 15000 bytes)
    # PIL mode "1" は行ごとにMSB先頭で詰める。400px = 50byte でちょうど割り切れる
    # ビットの意味: 1 = 白 / 0 = 黒 (framebuf.MONO_HLSB と同じ並び)
    (BASE / "sfl.bin").write_bytes(img.tobytes())
    print(f'{post["post_title"]} / {len(matches)}試合 を描画しました')


if __name__ == "__main__":
    main()