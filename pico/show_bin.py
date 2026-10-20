# show_bin.py -- 点灯確認用。ネットワークを使わず、Pico内の sfl.bin を表示するだけ。
#
# 前提:
#   1. この基板は 4.2inch B/W の **V2**(左下の B/W の丸が緑で V2 と表記)。
#      Waveshare のデモの **Pico-ePaper-4.2_V2.py** を使うこと。
#      V1用の Pico-ePaper-4.2.py は BUSY の極性が逆で、無限に待ち続ける。
#   2. ファイル名にハイフンとドットが入っていて import できないので、
#      **epd4in2.py にリネーム**して Pico に置く。
#   3. PC で render.py を実行して作った sfl.bin を Pico のルートに置く。
#
# クラス名もメソッド名も決め打ちせず、モジュールの中から探す。
# Waveshare は版によって EPD_4in2 / EPD_4in2_V2 などと名前が揺れるため。
#
# うまくいかないときは INVERT を True にして再実行(白黒が反転して見える場合)。

import epd4in2

BIN_PATH = "sfl.bin"
EXPECT = 400 * 300 // 8   # 15000
INVERT = False


def find_class():
    """epd4in2.py の中から EPD クラスを探す"""
    for name in ("EPD_4in2_V2", "EPD_4in2", "EPD_4IN2_V2", "EPD_4IN2", "EPD"):
        cls = getattr(epd4in2, name, None)
        if isinstance(cls, type):
            return name, cls

    found = [n for n in dir(epd4in2) if "EPD" in n.upper()]
    raise ImportError(
        "epd4in2.py に EPD クラスが見つからない。中にあるのは: {}\n"
        "  Pico-ePaper-4.2_V2.py を epd4in2.py として保存できているか確認する".format(
            found or "(何もない — 保存に失敗している可能性)"))


def find_methods(epd):
    """V1 と V2 でメソッド名が違うので、載っているほうを拾う"""
    for tag, init, disp in (
            ("V2", "EPD_4IN2_V2_Init", "EPD_4IN2_V2_Display"),
            ("V1", "EPD_4IN2_Init", "EPD_4IN2_Display")):
        if hasattr(epd, init) and hasattr(epd, disp):
            return tag, getattr(epd, init), getattr(epd, disp)
    raise AttributeError(
        "初期化/表示メソッドが見つからない。あるのは: {}".format(
            [n for n in dir(epd) if "4IN2" in n.upper()]))


def load(path=BIN_PATH):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) != EXPECT:
        raise ValueError(
            "サイズが違う: {} byte (期待値 {})。render.py の出力か確認する".format(
                len(data), EXPECT))
    return data


def blit(epd, data):
    """sfl.bin をドライバのフレームバッファへ流し込む。

    PIL の mode "1" の tobytes() は 1=白 / 0=黒 の MSB 先頭詰め。
    Waveshare のドライバも 0xff=白 の MONO_HLSB なので、そのまま代入できる。
    """
    buf = epd.buffer_1Gray
    if len(buf) != EXPECT:
        raise ValueError("ドライバのバッファが {} byte。想定と違う".format(len(buf)))
    if INVERT:
        for i in range(EXPECT):
            buf[i] = ~data[i] & 0xFF
    else:
        buf[:] = data
    return buf


def main():
    name, cls = find_class()
    print("クラス: {}".format(name))

    print("読み込み中...")
    data = load()

    print("ディスプレイ初期化中(数秒かかる)")
    epd = cls()
    tag, init, display = find_methods(epd)
    print("ドライバ: {}".format(tag))
    if tag == "V1":
        print("  ※この基板は V2。V1 のままだと busy で止まる")
    init()

    print("描画中(全画面リフレッシュに約4秒)")
    display(blit(epd, data))

    epd.Sleep()
    print("完了。電源を切っても表示は残る")


if __name__ == "__main__":
    main()
