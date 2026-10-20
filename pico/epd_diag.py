# epd_diag.py -- ePaper が busy から抜けない原因を切り分ける。
#
# Thonny で開いて実行(F5)。ドライバは不要、このファイル単体で動く。
# 出力を全部コピーして共有すること。

from machine import Pin, SPI
import time

BUSY_PIN, RST_PIN, DC_PIN, CS_PIN, CLK_PIN, DIN_PIN = 13, 12, 8, 9, 10, 11


def read_busy(pull, label):
    p = Pin(BUSY_PIN, Pin.IN, pull)
    time.sleep_ms(50)
    vals = [p.value() for _ in range(5)]
    print("  {:<10} -> {}".format(label, vals))
    return vals[0]


print("=" * 46)
print("1. BUSY ピンを何もせずに読む")
print("=" * 46)
up = read_busy(Pin.PULL_UP, "pull-up")
down = read_busy(Pin.PULL_DOWN, "pull-down")
read_busy(None, "no pull")

if up == 1 and down == 0:
    print("  判定: 浮いている。パネル側から信号が来ていない")
elif up == 0 and down == 0:
    print("  判定: Low に駆動されている。パネルが busy を主張し続けている")
elif up == 1 and down == 1:
    print("  判定: High に駆動されている。パネルは idle。")
    print("        ドライバの BUSY 極性が逆の可能性が高い")

print()
print("=" * 46)
print("2. ハードウェアリセット後の BUSY の動き")
print("=" * 46)
rst = Pin(RST_PIN, Pin.OUT)
busy = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)

rst.value(1); time.sleep_ms(20)
rst.value(0); time.sleep_ms(5)
rst.value(1)

changed = False
first = busy.value()
for i in range(30):
    v = busy.value()
    if v != first:
        changed = True
    print("  {:>4} ms  BUSY = {}".format(i * 50, v))
    time.sleep_ms(50)
print("  判定: リセットで BUSY が{}".format(
    "変化した(パネルは反応している)" if changed else "一切変化しない"))

print()
print("=" * 46)
print("3. POWER ON コマンド(0x04)を直接送る")
print("=" * 46)
spi = SPI(1, baudrate=4_000_000, sck=Pin(CLK_PIN), mosi=Pin(DIN_PIN))
dc = Pin(DC_PIN, Pin.OUT)
cs = Pin(CS_PIN, Pin.OUT)
cs.value(1)


def cmd(c):
    dc.value(0); cs.value(0); spi.write(bytes([c])); cs.value(1)


rst.value(1); time.sleep_ms(20)
rst.value(0); time.sleep_ms(5)
rst.value(1); time.sleep_ms(20)

cmd(0x04)   # POWER ON
ready = False
for i in range(30):
    v = busy.value()
    print("  {:>4} ms  BUSY = {}".format(i * 100, v))
    if v == 1:
        ready = True
        print("  → レディになった。UC8176 として正常な応答")
        break
    time.sleep_ms(100)

if not ready:
    print("  → 3秒待っても Low のまま")

print()
print("=" * 46)
print("診断おわり。この出力を全部コピーして共有すること")
print("=" * 46)
