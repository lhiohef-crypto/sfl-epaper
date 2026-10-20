# config.py の雛形。config.py という名前でコピーして WiFi を書き込む。
# config.py は WiFi パスワードを含むので .gitignore で除外している。

WIFI_SSID = "あなたのSSID"
WIFI_PASS = "あなたのパスワード"

BIN_URL = "https://raw.githubusercontent.com/lhiohef-crypto/sfl-epaper/main/sfl.bin"

# 次に起きるまでの時間(分)。6時間ごとなら 360。
# 火・金の深夜に Actions が更新するので、6時間おきに見に行けば十分間に合う。
SLEEP_MINUTES = 360

# 白黒が反転して見える場合だけ True
INVERT = False
