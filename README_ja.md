# 日本語ピッチアクセント Anki デッキ生成ツール

日本語ピッチアクセント学習用の Anki フラッシュカードを生成します。

- 色分けされたピッチパターン（赤＝高、青＝低）
- アクセント型番号 `[n]`（n＝下がり目の位置、0＝平板型）
- 動詞・形容詞の活用形ドリル

## 特長

一般的なピッチアクセントツールは辞書形のみを扱いますが、本ツールは：

1. **活用形を計算** - 食べる[2] → 食べない[2]、食べます[3] など
2. **複合名詞のアクセント結合** - 東京方言の連濁規則を適用
3. **数詞の読み変換** - 1952年 → せんきゅうひゃくごじゅうにねん

### 複合名詞の例

連濁規則なし（不正確）：
```
安全[0] + 保障[0] + 面[0] = 3つの別々の単語
```

連濁規則あり（本ツール）：
```
安全保障面 [7] = 1つの複合語、7拍目の後で下がる
```

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/rschein2/PitchAccent.git
cd PitchAccent

# 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または: venv\Scripts\activate  # Windows

# 依存パッケージをインストール
pip install -r requirements.txt

# UniDic辞書をダウンロード（約500MB、必須）
python -m unidic download
```

## 使い方

### テキストから生成
```bash
# 直接テキスト入力
python anki_generator.py --text "今日は天気がいいですね。" --output deck.tsv

# テキストファイルから
python anki_generator.py --input mybook.txt --output deck.tsv

# 対話モード（テキストを貼り付け、Ctrl+Dで終了）
python anki_generator.py --interactive --output deck.tsv
```

### 出力形式
```bash
# Ankiインポート形式（デフォルト）
python anki_generator.py --input text.txt --output deck.tsv

# スタンドアロンHTML（ブラウザで色付き表示可能）
python anki_generator.py --input text.txt --output study.html

# プレーンテキスト
python anki_generator.py --input text.txt --output study.txt
```

### Ankiへのインポート
1. Anki を開く → ファイル → インポート
2. `.tsv` ファイルを選択
3. フィールド区切りを「タブ」に設定
4. フィールドをマッピング：フィールド1 → 表面、フィールド2 → 裏面
5. **「フィールドにHTMLを使用」をチェック**

## 出力例

**表面：**
```
彼女は毎日図書館で本を読んでいる。
```

**裏面：**
```
彼女 かのじょ [1]
毎日 まいにち [1]
図書館 としょかん [2]
本 ほん [1]
読んでいる よんでいる [1]

── 活用形 ──
読む [1] HLL: 読んだ [1] HLLL, 読んで [1] HLLL, 読まない [2] LHLLL, 読みます [3] LHHLL
```

## アルゴリズム

### アクセント計算

UniDicの形態素解析とF型結合規則を使用：
- **F1**: 前部のアクセントを保持
- **F2**: 平板 → 境界にシフト、それ以外 → 保持
- **F3**: 平板 → 平板を維持、それ以外 → シフト
- **F4**: 常に境界にシフト
- など

詳細: [docs/f_type_rules.md](docs/f_type_rules.md)

### 複合名詞の連濁

東京方言のモーラ長に基づく規則を実装：

| N2の長さ | 規則 |
|----------|------|
| 1-2モーラ | N1の最終モーラにアクセント |
| 3-4モーラ（平板） | N2の第1モーラにアクセント |
| 3-4モーラ（起伏） | N2のアクセント位置を保持 |
| 5モーラ以上 | N2のアクセントを保持（平板ならそのまま） |

詳細: [docs/compound_sandhi.md](docs/compound_sandhi.md)

### 数詞のアクセント

宮崎らの研究に基づく数詞×助数詞カテゴリーシステムを実装。

詳細: [docs/numeral_accent.md](docs/numeral_accent.md)

## データソース

### UniDic（国語研短単位自動解析用辞書）

本ツールのピッチアクセントデータは主に **UniDic** から取得しています。

- **開発元**: 国立国語研究所（NINJAL）
- **基盤コーパス**: 日本語話し言葉コーパス（CSJ）、現代日本語書き言葉均衡コーパス（BCCWJ）
- **アクセントデータ**: 言語学者によってアノテーションされた東京方言標準
- **信頼性**: 学術研究・商用製品で広く使用される業界標準

UniDicは素人によるWiki的なデータではなく、専門の言語学者によって構築・維持されている権威あるリソースです。

### 精度について

- **一般語彙**: 高精度
- **複合語アクセント規則**: 約80-90%の精度（一部の複合語は語彙化された例外）
- **数詞の読み**: 連濁未対応（さんひゃく ではなく さんびゃく など）
- **非常に長い複合語**: アクセントが予測不能な場合あり

## ファイル構成

```
├── anki_generator.py          # メインCLIエントリーポイント
├── requirements.txt
│
├── pitch_accent/              # コアライブラリパッケージ
│   ├── __init__.py
│   ├── engine.py              # アクセント計算（F型規則）
│   ├── rules.json             # UniDic接尾辞結合規則
│   ├── compound.py            # 複合名詞の連濁
│   ├── numeral.py             # 助数詞カテゴリーとアクセント規則
│   ├── numeral_reading.py     # アラビア数字 → ひらがな変換
│   ├── parser.py              # トークン化と複合語検出
│   ├── formatter.py           # 色分けHTML出力
│   ├── corpus.py              # テキスト/ファイル入力処理
│   └── lookup.py              # オプション：JPDB検証用
│
├── docs/                      # 詳細ドキュメント
│   ├── compound_sandhi.md
│   ├── f_type_rules.md
│   └── numeral_accent.md
│
├── examples/                  # サンプル入力ファイル
│   └── japan_us_relations.txt
│
└── scripts/                   # 開発ユーティリティ
    ├── demo.py
    ├── compare_engines.py
    └── extract_rules.py
```

## 参考文献

- [UniDic](https://clrd.ninjal.ac.jp/unidic/) - 形態素解析辞書
- [TUFS言語モジュール](https://www.coelang.tufs.ac.jp/mt/ja/pmod/practical/02-07-01.php) - 複合語アクセント規則
- [宮崎ら（2012）](https://www.gavo.t.u-tokyo.ac.jp/~mine/paper/PDF/2012/ASJ_1-11-11_p319-322_t2012-3.pdf) - 数詞アクセント規則
- [OJAD](https://www.gavo.t.u-tokyo.ac.jp/ojad/) - オンライン日本語アクセント辞書
- [窪薗晴夫](https://scholar.google.com/citations?user=3MlvxUcAAAAJ) - 日本語韻律研究

## ライセンス

MIT
