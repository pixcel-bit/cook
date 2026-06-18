# 週次献立 自動生成 仕様書

毎週土曜 午前9時（JST）に Claude Code routine として自動実行される、作り置き献立の生成・公開システム。

---

## ファイル構成

| ファイル | 役割 | 更新タイミング |
|----------|------|---------------|
| `CLAUDE.md` | 本仕様書。routineが参照するルール | ルール変更時のみ |
| `preferences.json` | 可変ユーザーデータ（評価・リクエスト・残り食材・家族情報） | ユーザー操作・毎週 |
| `menu.json` | 今週の生成レシピデータ（SVG含む） | 毎週土曜に上書き |
| `index.html` | SPAアプリ本体。menu.jsonを読み込んで表示 | 機能追加時のみ |

**routineがpushするのは `menu.json` と `preferences.json`。** index.htmlは変更しない。

**ブランチ運用：`main` ブランチのみ使用。作業ブランチは作らない。**

---

## トリガー設計

- 実行方式：Claude Code `/schedule`（routine）
- 実行タイミング：**毎週土曜 午前9時（JST）**
- 手動実行時の起動ワード：「今週の献立お願い」「起動」「よろしく」など表現ゆれに対応
- PCオフでも実行される（Anthropicクラウド上で動作）

---

## インプット仕様

### 1. Gmailからの食材取得

```
検索条件: from:support@greenbeans.com
対象メール:
  - 件名「ご注文内容の変更を受付しました」
  - 件名「ご注文内容をご確認下さい」
  ※ 同一注文に複数ある場合は最新の1通のみ使用
  ※「商品をお届けしました」（お届け完了）メールは商品リストがないため無視

抽出箇所: メール本文の「■ご注文商品」セクション以降
フォーマット: 商品名 | 単価 | 数量 | 小計
```

### 食材名の正規化ルール

商品名から産地・容量・ブランド名・記号を除去して食材名に変換する。

| 商品名（メール記載） | 正規化後 |
|---------------------|---------|
| `[鮮度+] 新潟県産 まるごとえのき 150g 1袋` | えのき |
| `うまみ和豚 国産豚肉小間切れ 250g～350g 【冷蔵】トップバリュ` | 豚こま切れ |
| `純輝鶏むね肉 1kgパック 【冷蔵】トップバリュグリーンアイナチュラル 青森県産` | 鶏むね肉 |
| `[鮮度+] 千葉県産 へたなしミニトマト スイートベル 220g` | ミニトマト |

### 2. 残り食材の取得

`preferences.json` の以下を参照：
- `leftover_ingredients.checked`（チェックリスト）
- `leftover_ingredients.extra`（自由記述）

### 3. その他インプット

`preferences.json` から以下を取得：
- `weekly_request.moods`・`weekly_request.note`：今週のリクエスト
- `recipes[]` で `bad_count > 0`：除外メニュー
- `recipes[]` で `priority === true`：優先メニュー
- `family.child_birthdate`：子供の生年月日（実行時点で月齢を自動計算）

### 4. 常備ハーブ

`preferences.json` の `garden_herbs` を参照。
庭で育てているハーブのため常時入手可能だが、**必須ではない**。
合う料理・調理法がある場合に積極的に活用する程度でよい。
無理に全品に使う必要はない。

---

## 家族プロフィール

- 大人2人（Yusuke・Aya）＋ 子供1人
- 子供の生年月日は `preferences.json` の `family.child_birthdate` を参照し、**実行時点の年齢・月齢を計算して使用**（固定の年齢を書かない）
- 対象食事：月〜金の夜ごはん（5日分）
- 子供は辛いものが苦手 → 辛味は別添え。大人・子供で共通メニューにし、味付け前の取り分けで対応

---

## 調理器具と運用方針

### 保有調理器具

| 器具 | 用途・備考 |
|------|-----------|
| フライパン・鍋 | 手動調理担当 |
| ヘルシオ（ウォーターオーブン） | オーブン・レンジとして使用。**蒸し調理には使わない** |
| 蒸し器 | 蒸し料理専用 |
| グリル | 焼き物 |
| アラジン トースター | 焼き物・温め |
| ブラウン ハンドブレンダー マルチクイック5 Pro | 千切り・スライス（アタッチメント使用） |
| レコルト | 補助調理 |
| オートクッカー ビストロ | 煮込み・かき混ぜ全自動。設定値を手順に明記 |

### 調理オペレーション方針

- 作り置きは**土日のどちらか1日のみ**で完結（両日に分けない）
- 所要時間の目安：**90〜150分**（分刻みスケジュールは不要）
- **並列調理を前提**に組む
- 仕込みの順序：**ビストロ → ヘルシオ → 蒸し器 → フライパン**（放置度の高い順）
- 平日は「レンチンのみ」または「焼くだけ」で完成する状態に作り置き
- 下味冷凍を活用してよい

---

## レシピ生成ルール

- **主菜5品 ＋ 副菜2品**を基本構成
- 副菜は各2〜3日分として2品でカバー
- 曜日の割り当てはしない（何曜日に食べるかは本人が決める）
- ジャンルはバランスよく（和・洋・中こだわらない）
- 食材を使い切ることを意識する
- 使い切れない食材は「余り食材メモ」に使い道を記載
- 手持ち調味料（醤油・みりん・酒・砂糖・酢・ごま油・オイスターソース・鶏がらスープの素・コンソメ・ケチャップ・はちみつ・塩・こしょう等）は前提とし、注文食材以外で買い足しが必要なものは「買い足しリスト」に明記
- 低評価レシピ（bad_count > 0）は提案しない
- 優先レシピ（priority === true）は主菜・副菜の性質に合った方に必ず含める

---

## レシピ生成プロンプト（テンプレート）

```
あなたは家庭料理の献立アシスタントです。
以下の情報をもとに、今週の作り置き献立を提案してください。

## 家族構成・制約
- 大人2人 ＋ 子供1人（{child_age}歳{child_months}ヶ月）
- 子供は辛いものが苦手 → 辛味は別添え。できるだけ大人・子供で共通メニューにし、味付け前の取り分けで対応
- 週末（土日のどちらか1日）にまとめて作り置き（合計90〜150分以内）
- 平日は電子レンジか焼くだけで食べられる状態にすること

## 調理器具と仕込み順序
- ビストロ（オートクッカー）：煮込み・全自動。最初に仕込む。手順に「高圧・〇〇分」等の設定値を明記
- ヘルシオ（ウォーターオーブン）：オーブン・レンジ用途。蒸しには使わない。2番目に仕込む
- 蒸し器：蒸し料理専用。3番目
- グリル / アラジントースター：焼き物
- ブラウン ハンドブレンダー（マルチクイック5 Pro）：千切り・スライス
- フライパン・鍋：最後に手動で行う

## 今週の食材
【グリーンビーンズ配達分】
{delivery_ingredients}

【残り食材】
{leftover_ingredients}

## 今週のリクエスト
{weekly_request}
（未記入の場合はこのセクションを省略）

## 除外メニュー（低評価）
{bad_recipes}
（なければこのセクションを省略）

## 優先メニュー
{priority_recipes}
※ 料理の種類に応じて主菜・副菜の適切な方に含めてください
（なければこのセクションを省略）

## お願い
上記の食材を中心に使い、以下の形式でJSONのみ返してください。

- 主菜5品・副菜2品
- 副菜は各2〜3日分（材料は4人分）、主菜は2人分
- 各レシピに「料理名・使う食材・手順（3〜5ステップ）・調理時間・使用器具・子供メモ」を含める
- 手順に調理器具の具体的な設定値を含めること（例：ビストロ高圧15分）
- 食材を使い切ることを意識。使い切れないものはsurplus_noteに記載
- 買い足しが必要なものはshopping_listに記載
- 余計な説明文は不要。JSONのみ返すこと

## 出力形式
{
  "delivery_date": "YYYY-MM-DD",
  "delivery_ingredients": ["正規化済み食材名1", "正規化済み食材名2"],
  "main": [
    {
      "name": "料理名",
      "tool": "フライパン",
      "freeze": false,
      "ingredients": ["食材1", "食材2"],
      "steps": ["手順1", "手順2", "手順3"],
      "time_minutes": 20,
      "storage_note": "冷蔵3日",
      "kid_note": "取り分けのポイント（不要なら省略）",
      "svg": "<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'>...</svg>"
    }
  ],
  "side": [
    {
      "name": "料理名",
      "tool": "レンジ",
      "freeze": false,
      "ingredients": ["食材1", "食材2"],
      "steps": ["手順1", "手順2"],
      "time_minutes": 10,
      "storage_note": "冷蔵4日",
      "kid_note": "取り分けのポイント（不要なら省略）",
      "svg": "<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'>...</svg>"
    }
  ],
  "shopping_list": ["買い足し品1", "買い足し品2"],
  "surplus_note": "余り食材の使い道メモ"
}
```

### SVG生成ルール

- 各レシピに料理を表現するオリジナルSVGイラストを生成
- サイズ：`viewBox="0 0 100 100"`（width/height属性は不要）
- スタイル：温かみのある手描き風
- カラーパレット：ベース `#f7f4ec` / アクセント `#c0623a` 系に統一
- 著作権フリー（外部画像・実写は使わない）

**必須の描画要素（以下をすべて含めること）：**
1. **`<defs>` に `radialGradient` を定義**して皿・食材・ソースに適用する（単色塗りつぶし禁止）
2. **皿を必ず描く**（テーブル影 → リム外周影 → 皿本体グラデーション → 内側白 → ハイライトの順で重ねる）
3. **食材は皿の内側（cy≈79, ry≈7 の楕円内）に収まる高さに配置**し、浮かないよう接地影（低opacity楕円）を足元に置く
4. **食材の形は不規則な `<path>` で描く**（楕円の積み重ねのみは禁止）。暗部→中層→表面の3層で立体感を出す
5. **テクスチャを入れる**：焼き目・繊維・スペキュラハイライト（低opacity曲線）
6. **薬味・トッピングを添える**：ねぎ・ごま・ハーブなど料理に合わせて
7. **湯気を3〜5本描く**（ゆらぎのある曲線、opacity 0.2〜0.4）

**参考SVG（照り焼き鶏）— このクオリティを基準とすること：**

```
<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'><defs><radialGradient id='plate' cx='38%' cy='32%' r='62%'><stop offset='0%' stop-color='#ffffff'/><stop offset='100%' stop-color='#eeeae0'/></radialGradient><radialGradient id='g1' cx='30%' cy='25%' r='70%'><stop offset='0%' stop-color='#e88848'/><stop offset='55%' stop-color='#c05020'/><stop offset='100%' stop-color='#7a2e08'/></radialGradient><radialGradient id='g2' cx='36%' cy='28%' r='66%'><stop offset='0%' stop-color='#e07a42'/><stop offset='50%' stop-color='#b84818'/><stop offset='100%' stop-color='#6a2406'/></radialGradient><radialGradient id='sauce' cx='40%' cy='40%' r='60%'><stop offset='0%' stop-color='#a04020' stop-opacity='0.5'/><stop offset='100%' stop-color='#4a1604' stop-opacity='0.15'/></radialGradient></defs><rect width='100' height='100' fill='#f7f4ec'/><ellipse cx='51' cy='87' rx='37' ry='5.5' fill='#b0aca0' opacity='0.32'/><ellipse cx='51' cy='82' rx='36' ry='9' fill='#ccc9c0' opacity='0.5'/><ellipse cx='50' cy='81' rx='36' ry='9' fill='url(#plate)' stroke='#dedad2' stroke-width='0.8'/><ellipse cx='50' cy='79.5' rx='29' ry='7' fill='#fefefd'/><path d='M18 76 Q33 69 50 70' stroke='#ffffff' stroke-width='2' fill='none' opacity='0.6' stroke-linecap='round'/><path d='M32 79 Q40 76 50 77 Q61 76 68 79 Q63 82 50 81 Q37 82 32 79Z' fill='url(#sauce)'/><ellipse cx='43' cy='79' rx='19' ry='3' fill='#3a1004' opacity='0.22'/><path d='M25 77 Q31 72 44 73 Q57 72 61 77 Q59 80 44 79 Q29 80 25 77Z' fill='#6a2808'/><path d='M26 76 Q33 71 44 72 Q56 71 60 76 Q57 79 44 78 Q31 79 26 76Z' fill='#9a3e18'/><path d='M27 75 Q34 70 43 70.5 Q50 69 57 71 Q61 74 58 77 Q52 79 43 78 Q32 78 27 75Z' fill='url(#g1)'/><path d='M29 74 Q36 71 45 72 Q52 71 57 74' stroke='#4a1604' stroke-width='1.3' fill='none' opacity='0.35' stroke-linecap='round'/><path d='M31 76.5 Q38 74 46 74.5 Q53 74 58 76' stroke='#4a1604' stroke-width='0.9' fill='none' opacity='0.28' stroke-linecap='round'/><path d='M30 73 Q37 71.5 44 72.5' stroke='#c05828' stroke-width='0.7' fill='none' opacity='0.45'/><path d='M34 71.5 Q42 70 50 71' stroke='#b85020' stroke-width='0.7' fill='none' opacity='0.38'/><path d='M45 70.5 Q52 70 57 72' stroke='#c05828' stroke-width='0.7' fill='none' opacity='0.38'/><path d='M30 72 Q35 69.5 41 71' stroke='#f8c090' stroke-width='2.5' fill='none' opacity='0.3' stroke-linecap='round'/><ellipse cx='33' cy='71' rx='3.5' ry='1.5' fill='#ffe8c8' opacity='0.28'/><ellipse cx='59' cy='74' rx='17' ry='2.8' fill='#3a1004' opacity='0.2'/><path d='M44 72 Q51 67 62 67 Q71 67 74 71.5 Q72 75.5 62 76 Q51 77 44 72Z' fill='#6a2808'/><path d='M45 71 Q52 66 62 66 Q70 66 73 70.5 Q71 74 62 74.5 Q52 75 45 71Z' fill='#9a3c18'/><path d='M46 70 Q50 65 60 65 Q67 64.5 71 68 Q72 71 69 73 Q63 74 57 73.5 Q50 74 46 70Z' fill='url(#g2)'/><path d='M47 69 Q53 65.5 61 66 Q66 65.5 70 68.5' stroke='#4a1604' stroke-width='1.3' fill='none' opacity='0.35' stroke-linecap='round'/><path d='M48 71.5 Q55 69 63 69.5 Q68 69.5 71 71.5' stroke='#4a1604' stroke-width='0.9' fill='none' opacity='0.28' stroke-linecap='round'/><path d='M49 69 Q56 67 63 68' stroke='#c05828' stroke-width='0.7' fill='none' opacity='0.42'/><path d='M52 67 Q59 65.5 65 66.5' stroke='#b84e20' stroke-width='0.7' fill='none' opacity='0.36'/><path d='M57 65.5 Q63 65 68 67' stroke='#c05828' stroke-width='0.7' fill='none' opacity='0.36'/><path d='M49 68 Q54 65.5 61 67' stroke='#f8c090' stroke-width='2.5' fill='none' opacity='0.3' stroke-linecap='round'/><ellipse cx='52' cy='66' rx='4' ry='1.5' fill='#ffe8c8' opacity='0.26'/><path d='M51 75 Q53 77 52 80' stroke='#7a2e08' stroke-width='1.3' fill='none' opacity='0.35' stroke-linecap='round'/><path d='M44 76 Q43 78 44 80' stroke='#8a3810' stroke-width='1' fill='none' opacity='0.25' stroke-linecap='round'/><path d='M30 64 Q37 61 46 63.5' stroke='#3a6c18' stroke-width='2.3' fill='none' stroke-linecap='round'/><path d='M33 62.2 Q41 59 51 61' stroke='#4e8224' stroke-width='1.7' fill='none' stroke-linecap='round'/><path d='M55 63 Q61 60.5 68 62.5' stroke='#3a6c18' stroke-width='1.9' fill='none' stroke-linecap='round'/><path d='M57.5 61 Q64 58.5 72 60.5' stroke='#4e8224' stroke-width='1.4' fill='none' stroke-linecap='round'/><line x1='38' y1='62.5' x2='38.5' y2='64.2' stroke='#2a5010' stroke-width='0.8' opacity='0.5'/><line x1='43' y1='62' x2='43.5' y2='63.5' stroke='#2a5010' stroke-width='0.8' opacity='0.5'/><line x1='62' y1='62' x2='62.5' y2='63.5' stroke='#2a5010' stroke-width='0.8' opacity='0.5'/><ellipse cx='43' cy='69.5' rx='1.5' ry='1' fill='#e4c870' transform='rotate(-28 43 69.5)'/><ellipse cx='50' cy='67.5' rx='1.5' ry='0.95' fill='#d8bc60' transform='rotate(12 50 67.5)'/><ellipse cx='59.5' cy='70.5' rx='1.3' ry='0.9' fill='#e4c870' transform='rotate(-12 59.5 70.5)'/><ellipse cx='45.5' cy='75.5' rx='1.4' ry='0.85' fill='#d8bc60' transform='rotate(30 45.5 75.5)'/><ellipse cx='55' cy='74' rx='1.3' ry='0.85' fill='#e4c870' transform='rotate(-6 55 74)'/><ellipse cx='63.5' cy='67' rx='1.2' ry='0.8' fill='#d8bc60' transform='rotate(20 63.5 67)'/><ellipse cx='37' cy='73' rx='1.2' ry='0.8' fill='#e4c870' transform='rotate(-18 37 73)'/><ellipse cx='67' cy='70' rx='1.1' ry='0.75' fill='#d8bc60' transform='rotate(8 67 70)'/><path d='M29 53 Q26 47 28 41 Q30 36 28 30' stroke='#bab6ac' stroke-width='1.8' fill='none' stroke-linecap='round' opacity='0.38'/><path d='M50 51 Q47 44 50 38 Q53 32 50 26' stroke='#bab6ac' stroke-width='1.8' fill='none' stroke-linecap='round' opacity='0.38'/><path d='M71 53 Q74 46 72 40 Q70 34 72 28' stroke='#bab6ac' stroke-width='1.8' fill='none' stroke-linecap='round' opacity='0.38'/><path d='M39 52 Q37 46 39 40' stroke='#c8c5bc' stroke-width='1.1' fill='none' stroke-linecap='round' opacity='0.22'/><path d='M61 52 Q63 46 61 40' stroke='#c8c5bc' stroke-width='1.1' fill='none' stroke-linecap='round' opacity='0.22'/></svg>
```

---

## アウトプット仕様

### menu.json の保存

生成したJSONを `menu.json` としてリポジトリルートに保存・push する。

```
push先: pixcel-bit/cook リポジトリ main ブランチ
ファイル: menu.json（毎週上書き）
注意: index.html は変更しない
```

### index.html との連携

index.htmlはmenu.jsonをfetchして「メニュータブ」を動的に描画する。

### preferences.json の更新（採用レシピ反映）

menu.json を生成・push した後、以下のスクリプトを実行して preferences.json を更新し push する。

```
node scripts/update_prefs.js
```

このスクリプトが以下を確実に実行する（deterministic logic）：
- `weekly_request` を `{ moods: [], note: "", updated_at: null }` にリセット
- `leftover_ingredients` を `{ checked: [], extra: "", updated_at: null }` にリセット

**注意：`recipes[]` には触れない。** レシピリストはユーザーが👍を押したか手動登録したものだけで構成される。ルーティンが自動追加しない。

```
push先: pixcel-bit/cook リポジトリ main ブランチ
ファイル: preferences.json（スクリプト実行後に push）
```

---

## セキュリティ注意事項

- このリポジトリは**public**のため、個人情報はCLAUDE.mdに書かない
- 子供の生年月日は `preferences.json` の `family.child_birthdate` に保存し、ここからは参照のみ
- GitHubトークン・APIキーはコードに直接書かない
- pushするのは `menu.json` と `preferences.json` のみ。他ファイル・ブランチには触れない
