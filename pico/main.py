# main.py -- 起動するたびに sfl.bin を取りに行き、変化があれば描き直して寝る。
#
# 前提:
#   epd4in2.py   Waveshare の Pico-ePaper-4.2.py をリネームしたもの
#   config.py    WiFi と URL の設定
#
# 設計方針:
#   - 取得に失敗しても画面には触らない。e-paper は電源が切れても表示が残るので、
#     「前回の結果が出たまま」が最も無害な失敗の仕方になる。
#   - 中身が前回と同じならリフレッシュしない。全画面更新は4秒かかり、
#     パネルの寿命も削るので、無駄打ちは避ける。

import gc
import machine
import network
import time

import config

EXPECT = 400 * 300 // 8   # 15000
STAMP = "last.txt"        # 前回描いた内容の指紋
WIFI_TIMEOUT = 30         # 秒


def log(msg):
    print("[{}] {}".format(time.ticks_ms(), msg))


# ---------------------------------------------------------------- WiFi

def wifi_connect():
    import rp2
    rp2.country("JP")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # 省電力モードのままだと接続が status=1 で止まることがある
    wlan.config(pm=0xa11140)
    if not wlan.isconnected():
        log("WiFi 接続中: {}".format(config.WIFI_SSID))
        wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
        for _ in range(WIFI_TIMEOUT * 2):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    if not wlan.isconnected():
        raise OSError("WiFi に接続できない (status={})".format(wlan.status()))
    log("接続完了 {}".format(wlan.ifconfig()[0]))
    return wlan


def wifi_off(wlan):
    try:
        wlan.disconnect()
        wlan.active(False)
    except Exception:
        pass


# ---------------------------------------------------------------- 取得

def fetch(url):
    import urequests
    log("取得中: {}".format(url))
    r = urequests.get(url)
    try:
        if r.status_code != 200:
            raise OSError("HTTP {}".format(r.status_code))
        data = r.content
    finally:
        r.close()
    if len(data) != EXPECT:
        raise ValueError("サイズが違う: {} byte".format(len(data)))
    log("取得完了 {} byte".format(len(data)))
    return data


def fingerprint(data):
    """内容の指紋。衝突しても実害がないので単純な加算で足りる"""
    h = 0
    for i in range(0, EXPECT, 7):     # 全バイト舐めると遅いので間引く
        h = (h * 31 + data[i]) & 0xFFFFFFFF
    return "{:08x}-{}".format(h, len(data))


def unchanged(fp):
    try:
        with open(STAMP) as f:
            return f.read().strip() == fp
    except OSError:
        return False


def remember(fp):
    try:
        with open(STAMP, "w") as f:
            f.write(fp)
    except OSError as e:
        log("指紋を保存できない: {}".format(e))


# ---------------------------------------------------------------- 表示

def show(data):
    # クラス名もメソッド名も版によって揺れるので決め打ちしない
    import epd4in2
    cls = None
    for n in ("EPD_4in2_V2", "EPD_4in2", "EPD_4IN2_V2", "EPD_4IN2", "EPD"):
        c = getattr(epd4in2, n, None)
        if isinstance(c, type):
            cls = c
            log("クラス: {}".format(n))
            break
    if cls is None:
        raise ImportError("epd4in2.py に EPD クラスがない")

    epd = cls()
    # この基板は V2(BUSY は HIGH=busy)
    if hasattr(epd, "EPD_4IN2_V2_Init"):
        init, display = epd.EPD_4IN2_V2_Init, epd.EPD_4IN2_V2_Display
    else:
        init, display = epd.EPD_4IN2_Init, epd.EPD_4IN2_Display
    init()

    buf = epd.buffer_1Gray
    if config.INVERT:
        for i in range(EXPECT):
            buf[i] = ~data[i] & 0xFF
    else:
        buf[:] = data

    log("描画中")
    display(buf)
    epd.Sleep()
    log("描画完了")


# ---------------------------------------------------------------- 本体

def run():
    wlan = None
    try:
        wlan = wifi_connect()
        data = fetch(config.BIN_URL)
    except Exception as e:
        log("取得に失敗: {}: {}".format(type(e).__name__, e))
        log("画面はそのままにして寝る")
        return
    finally:
        if wlan:
            wifi_off(wlan)

    fp = fingerprint(data)
    if unchanged(fp):
        log("前回と同じ内容。リフレッシュを省略")
        return

    gc.collect()
    show(data)
    remember(fp)


def sleep_and_restart():
    ms = int(config.SLEEP_MINUTES) * 60 * 1000
    log("{} 分スリープ".format(config.SLEEP_MINUTES))
    machine.deepsleep(ms)   # 復帰時はリセットされ main.py が再実行される


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log("想定外のエラー: {}: {}".format(type(e).__name__, e))
    sleep_and_restart()
