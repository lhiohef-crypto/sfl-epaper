# config.py -- 環境ごとの設定。これだけ書き換える。

WIFI_SSID = "あなたのSSID"
WIFI_PASS = "あなたのパスワード"

# GitHub に push したあとの raw URL に差し替える。
# 例: https://raw.githubusercontent.com/miyagi/sfl-epaper/main/sfl.bin
BIN_URL = "https://raw.githubusercontent.com/USER/REPO/main/sfl.bin"

# 次に起きるまでの時間(分)。6時間ごとなら 360。
# 火・金の深夜に Actions が更新するので、6時間おきに見に行けば十分間に合う。
SLEEP_MINUTES = 360

# 白黒が反転して見える場合だけ True
INVERT = False
