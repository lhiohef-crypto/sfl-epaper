# SFL e-Paper プロジェクト

Street Fighter League Pro-JP 2026 の試合結果を、Raspberry Pi Pico 2 W +
Waveshare Pico-ePaper-4.2 (400×300 白黒) に自動表示する。

## 現在地（2026-10-20 時点）

**動いているもの**
- API から結果を取得して 400×300 の1bit画像を生成するところまで完成
- 実機表示も成功済み（2026-09-11、Division S 第2節を表示）
- リポジトリ公開済み: https://github.com/lhiohef-crypto/sfl-epaper （Public）
- Actions は手動実行で動作確認済み（2026-10-20）。cron で自動稼働中
- raw URL から `sfl.bin`（15000 byte）が取れることを確認済み:
  `https://raw.githubusercontent.com/lhiohef-crypto/sfl-epaper/main/sfl.bin`

- Pico の `main.py`（WiFi → 取得 → 描画 → deepsleep）も実機で動作確認済み（2026-10-20）。
  本番稼働中

## Pico のメモ

- WiFi は **2.4GHz の `HUMAX-22B81`** を使う。`-A` は 5GHz で Pico 2 W からは見えない
  （status=-2 = SSID が見つからない）
- `rp2.country("JP")` と `wlan.config(pm=0xa11140)`（省電力オフ）を main.py に入れてある。
  status=1 のまま止まる症状への対策
- `config.py` は gitignore 対象（WiFi パスワード入り）。雛形は `config.example.py`
- 動作中の Pico に入るには、USB 挿し直し直後の約10秒以内に Thonny の停止ボタンを連打。
  入れたら `os.rename('main.py', 'app.py')` → `import app; app.run()` で眠らずに試せる
  （`import app` は2回目以降読み直さないので、変更後は `machine.soft_reset()` を挟む）

## git まわりのメモ

- git / gh は `C:\Program Files\Git\cmd` と `C:\Program Files\GitHub CLI` にある。
  エージェントのシェルでは PATH に無いことがあるので、通らなければ追加する
- コミット作者は noreply アドレス（`345278613+lhiohef-crypto@users.noreply.github.com`）
- Actions は **cache.json に差分があるときだけ** コミットする。
  画像はフッタの更新時刻（JST）が毎回変わるので差分判定に使えない
- `Noto_Sans_JP/` は未使用なので gitignore。使うのはルートの2つの ttf

## 環境

- Windows。作業フォルダは `C:\Users\lhioh\OneDrive\デスクトップ\SFL_results`
- Python 3.14（`requests` と `Pillow` 導入済み）
- **このマシンからは SFL の API に普通にアクセスできる。**
  以前 Cowork セッションで作業したときは組織の egress ポリシーで 403 になり、
  ブラウザ経由で取得する迂回が必要だった。その制約はここには無い。
  `python sfl.py` や `python render.py` をそのまま実行してよい
- **Pico への書き込みは Thonny で人間が手作業**。ここからは触れない。
  Pico 側のコードを変更したら「Thonny でこれをアップロードしてほしい」と伝えること

## ファイル構成

```
SFL_results/
├── sfl.py              API取得 + CLI表示。fetch() は cache.json フォールバック付き
├── render.py           画像生成。preview.png / preview_2x.png / sfl.bin を出力
├── cache.json          APIレスポンスのキャッシュ（取得成功時に自動更新）
├── logos/              チームロゴ 600×600 RGBA。_prev/ に旧版
├── NotoSansJP-*.ttf    フォント
├── requirements.txt
├── .gitignore
├── .github/workflows/update.yml
└── pico/               Pico に載せるコード（PC 側では実行できない）
    ├── show_bin.py     点灯確認用。ローカルの sfl.bin を表示するだけ
    ├── main.py         本番。WiFi → 取得 → 変化があれば描画 → deepsleep
    ├── config.py       WiFi と URL（要記入）
    ├── epd_diag.py     BUSY ピン切り分け用
    └── show_bin_main_ref.py   ← 消してよい。コミットミスで残った main.py の複製
```

## API

```
GET https://sf.esports.capcom.com/api/sfl2026/?data=results
ヘッダ: x-fd-mode: retrieve_all   ← 必須
        Referer: https://sf.esports.capcom.com/sfl2026/schedule/
```

レスポンス構造:
- `data.teams{key: {name, division("s"/"f"), point, battle_diff, round_diff}}`
- `data.schedules[].post_title` — "Division S 第2節" など
- `data.schedules[].fields.section.time` — "2026-09-01 00:00:00"
- `data.schedules[].fields.section.match1..4`
  — `{use: "show"/"hide", home, away, result}`
- **未実施の節は `result` が空文字列 `""`**（dict ではない）。型で判定すること
- `result.winner` は `"home"` / `"away"`、`result.total.point.{home,away}`

`sfl.latest_finished()` が「結果が入っている節のうち最新」を返す。

## 出力形式

| ファイル | 内容 |
|---|---|
| `preview.png` | 400×300 1bit PNG |
| `preview_2x.png` | 目視確認用の2倍拡大（gitignore 対象） |
| `sfl.bin` | **Pico 用の生1bppバッファ、ちょうど 15000 byte** |

`sfl.bin` は PIL の mode `"1"` の `tobytes()` そのまま。行ごと MSB 先頭、
400px = 50byte で端数なし。**1=白 / 0=黒** で、Waveshare ドライバの
`buffer_1Gray`（framebuf.MONO_HLSB、`fill(0xff)` が白）と完全に一致する。
**変換は不要。実機で検証済み。**

MicroPython で PNG をデコードするのは面倒なので Pico は `.bin` を読む。

## 描画の制約

- **実寸は 84.8 × 63.6 mm（120dpi）。想像よりかなり小さい**
  - ロゴ 66px = 14mm（親指の爪くらい）
  - スコア 32px = 6.8mm
  - フッタ 10px = 2.1mm（紙の6pt相当。これが下限）
- e-ink のコントラストはモニタより一段浅い。
  画面で「ギリギリ読める」ものは実機で読めない。**迷ったら太らせる**
- レイアウト: ヘッダ36px / 各行84px×3 / フッタ罫線 y=288。**現状3試合固定**
- `WINNER_STYLE = "none"`。勝敗マーカーは「不要」と判断済み。
  実装は残っているので `"badge"` / `"underline"` / `"frame"` に切替可能。
  **勝手に有効化しないこと**

## ロゴの2値化（ここは試行錯誤済み。壊さないこと）

ディザ（FLOYDSTEINBERG）は 66px では潰れるので**廃止した**。閾値方式・ディザなし。

3方式:
- `white`（既定） — 白背景に合成してそのまま2値化
- `invert` — 黒背景に合成して反転（白抜き／淡い色のロゴ用）
- `alpha` — 不透明部分をそのまま黒に（シルエット化）

現在の設定:
- `LOGO_MODE = {"dng": "alpha"}` のみ。他は既定の white
  - dng は黒と白が同一ロゴ内に混在するため、white/invert では必ず片方が消える
- `LOGO_TH_DEFAULT = 150`、上書きは `varrel=175, cr=130, ixa=130`

### ロゴ素材を追加・差し替えるとき

**生成AIから得た画像は透過されていないことが多い。** 市松模様が実ピクセルとして
焼き込まれた RGB だったり、単色グレー背景だったりする。

透過を再構築する手順:
1. 背景候補の輝度域を決める（市松なら 205-255、単色グレー背景なら 100-175）
2. **画像の縁から連結成分を塗りつぶして背景を判定する（flood fill）**
   単純な閾値だと ibsg の白文字や rid の白目のような「囲まれた白」まで
   背景扱いされて穴が開く
3. bbox でクロップ → 正方キャンバス中央配置 → 600×600 にリサイズ

`fav` だけ旧素材のまま（差し替え画像が来ていない）。

## ハードウェア

**配線作業は無い。** オンボードのメスヘッダに Pico を直挿し。レベル変換も基板上。
**USB は右向き**（基板右端の `USB` シルクに合わせる）。

### ⚠ この個体は V2

基板左下の `B/W` の丸が緑で「V2」と印字されている。**BUSY の極性が V1 と逆。**

| | BUSY = 0 | BUSY = 1 |
|---|---|---|
| V1 | busy | idle |
| **V2** | **idle** | **busy** |

V1 用ドライバ（`Pico-ePaper-4.2.py`）を使うと `e-Paper busy` で永久に止まる。
**必ず `Pico-ePaper-4.2_V2.py` を使う**
（https://github.com/waveshareteam/Pico_ePaper_Code の `python/` 配下。
組織名は `waveshareteam`。`waveshare` は存在しない）。

動いている証拠は、シェルに `e-Paper busy` の次に **`e-Paper busy release`** が出ること。

### ピン配置（デバッグ用の記録）

| e-Paper | Pico |
|---|---|
| DIN | GP11 (SPI MOSI) |
| CLK | GP10 (SPI SCK) |
| CS | GP9 |
| DC | GP8 |
| RST | GP12 |
| BUSY | GP13 |
| VCC | VSYS |

SPI は `SPI(1)`、baudrate 4,000,000。ユーザーキーは KEY0=GP15 / KEY1=GP17。

### ドライバ API

クラス `EPD_4in2` / `buffer_1Gray` = 15000 byte / `image1Gray` は
framebuf.MONO_HLSB / `fill(0xff)` が白 / `Sleep()`。
初期化と表示だけ V2 は `EPD_4IN2_V2_Init` / `EPD_4IN2_V2_Display`。

`pico/show_bin.py` と `pico/main.py` はクラス名もメソッド名も実行時に探すので、
V1/V2 どちらを置いても動くか、明示的に落ちる。

### Pico へのファイル転送（Thonny、人間の作業）

**「名前を付けて保存」は使わない。** 別のタブがアクティブだと空ファイルができ、
エラーも出ないので気づけない。実際にこれで詰まった。

正しい手順:
1. 上段（このコンピュータ）でファイルを右クリック →「/ へアップロード」
2. リネームが必要なものはシェルで `os.rename('元', '新')`

`Pico-ePaper-4.2_V2.py` はハイフンとドットを含むのでモジュール名として不正。
Pico 上では `epd4in2.py` にリネームすること。

`sfl.bin` はバイナリなので Thonny のエディタで開かない（`Bad encoding` が出る）。

## GitHub Actions（作成済み・未稼働）

`.github/workflows/update.yml`:
- cron `0 15,18 * * 2,5` (UTC) = JST 水・土の 00:00 と 03:00。取りこぼし対策で2回
- `workflow_dispatch` で手動実行可
- `permissions: contents: write`
- 差分が無ければコミットをスキップ
- コミット対象: `preview.png` / `sfl.bin` / `cache.json`

SFL の本節は毎週火曜・金曜。試合終了は22時頃なのでその後に走らせている。

## 電源（検討済み・結論は保留。当面 USB 給電）

- **ePaper は無視できる。** リフレッシュ 26.4mW/4秒、待機 <0.01µA。
  電源が切れても表示は残る
- **ボトルネックは Pico 2 W。** idle 38mA / WiFi 60mA /
  `machine.deepsleep()` でも **22mA**（旧 Pico W の 16mA より悪化している）
- 週2回更新の収支: 実作業 約1mAh/週 に対し、寝ている時間が約3,700mAh/週。
  **「働く」のはタダで「寝る」のが高い**
- 5,000mAh 1セル LiPo を VSYS 直結（VSYS は 1.8〜5.5V 入力なので昇圧不要）:
  - deepsleep のみ → 約9日
  - TPL5110（待機35nA）で物理的に電源を切る → 1年以上
- **モバイルバッテリーは不可。** 実効 3,300mAh 程度に目減りするうえ、
  消費電流が小さいと自動シャットオフする。省電力にするほど確実に死ぬ

## 残タスク

1. 次の節（Division F 第4節）で自動更新されたか確認する
2. ケース（3Dプリント）
3. `fav` ロゴの差し替え（任意）
4. 4試合目がある節への対応（現状3試合固定）、順位表の表示（未検討）
5. 電源方式の決定
6. workflow の `actions/checkout@v4` / `setup-python@v5` が Node 20 非推奨の警告。
   今は動くが、いずれ新しいメジャー版へ上げる

## 進め方

- **日本語で**
- 部分的な diff ではなく、**動く完全なコードを**出す
- 判断を委ねられたら（「おまかせ」）、理由を一言添えて決めて進める
- 変更したら `python render.py` を実行し、`preview_2x.png` を見て確認する
- Pico に関わる作業は、こちらからは実行できないので手順として提示する
