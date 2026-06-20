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

- 実行方式：Claude Code `/schedule`（routine）または手動実行
- スケジュール実行タイミング：**毎週土曜 午前9時（JST）**
- 手動実行時の起動ワード：「今週の献立お願い」「起動」「よろしく」など表現ゆれに対応
- PCオフでも実行される（Anthropicクラウド上で動作）

### スキップ判定（スケジュール実行時のみ）

スケジュール実行の場合、以下の手順でスキップ判定を行う。**手動実行の場合はこの判定を行わず、必ず生成する。**

1. Gmailから最新の「注文を受付しました」メールのお届け日を取得する
2. `menu.json` の `delivery_date` と比較する
3. **一致する場合 → 処理済みとしてスキップ**（「今週分は生成済みのためスキップしました」とログ出力して終了）
4. 一致しない場合 → 通常通り献立を生成する

---

## インプット仕様

### 1. Gmailからの食材取得

```
検索条件: from:support@greenbeans.com
対象メール:
  - 件名「注文を受付しました」
  - 件名「ご注文内容の変更を受付しました」
  - 件名「ご注文内容をご確認下さい」
  ※ 同一注文に複数ある場合は最新の1通のみ使用
  ※「商品をお届けしました」（お届け完了）メールは商品リストがないため無視
  ※「ご注文内容をご確認下さい」は発送通知メールの場合があり商品リストを含まないことがある。その場合は他のメールを使用する

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

- **主菜5品 ＋ 副菜3品**を基本構成
- 副菜は各2〜3日分として3品でカバー
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

- 主菜5品・副菜3品
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
2. **皿は小さく下寄せ**（cy≈87, rx≈37, ry≈7.5）。テーブル影 → リム外周影 → 皿本体グラデーション → 内側白 → ハイライトの順で重ねる
3. **食材を大きく描く**（y=59〜84の範囲を使い切る）。接地影（低opacity楕円）を足元に置く
4. **食材の形は不規則な `<path>` で描く**（楕円の積み重ねのみは禁止）。暗部→中層→表面の3層で立体感を出す
5. **テクスチャを入れる**：焼き目・繊維・スペキュラハイライト（低opacity曲線）
6. **薬味・トッピングを添える**：ねぎ・ごま・ハーブなど料理に合わせて
7. **湯気を3〜5本描く**（ゆらぎのある曲線、opacity 0.2〜0.4）

**参考SVG（照り焼き鶏）— このクオリティを基準とすること：**

```
<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'><defs><radialGradient id='plate' cx='38%' cy='32%' r='62%'><stop offset='0%' stop-color='#ffffff'/><stop offset='100%' stop-color='#eeeae0'/></radialGradient><radialGradient id='g1' cx='30%' cy='25%' r='70%'><stop offset='0%' stop-color='#e88848'/><stop offset='55%' stop-color='#c05020'/><stop offset='100%' stop-color='#7a2e08'/></radialGradient><radialGradient id='g2' cx='36%' cy='28%' r='66%'><stop offset='0%' stop-color='#e07a42'/><stop offset='50%' stop-color='#b84818'/><stop offset='100%' stop-color='#6a2406'/></radialGradient><radialGradient id='sauce' cx='40%' cy='40%' r='60%'><stop offset='0%' stop-color='#a04020' stop-opacity='0.5'/><stop offset='100%' stop-color='#4a1604' stop-opacity='0.15'/></radialGradient></defs><rect width='100' height='100' fill='#f7f4ec'/><ellipse cx='51' cy='92' rx='38' ry='6' fill='#b0aca0' opacity='0.32'/><ellipse cx='51' cy='88' rx='37' ry='7.5' fill='#ccc9c0' opacity='0.5'/><ellipse cx='50' cy='87' rx='37' ry='7.5' fill='url(#plate)' stroke='#dedad2' stroke-width='0.8'/><ellipse cx='50' cy='86' rx='30' ry='5.5' fill='#fefefd'/><path d='M17 83 Q33 76 50 77' stroke='#ffffff' stroke-width='2' fill='none' opacity='0.6' stroke-linecap='round'/><path d='M28 84 Q38 81 50 82 Q63 81 72 84 Q66 87 50 86 Q34 87 28 84Z' fill='url(#sauce)'/><ellipse cx='42' cy='83' rx='22' ry='4' fill='#3a1004' opacity='0.22'/><path d='M18 80 Q24 70 42 71 Q60 70 66 80 Q63 85 42 84 Q21 85 18 80Z' fill='#6a2808'/><path d='M19 79 Q25 69 42 70 Q59 69 65 79 Q62 83 42 82 Q22 83 19 79Z' fill='#9a3e18'/><path d='M20 77 Q27 67 42 68 Q56 66 63 77 Q60 81 42 80 Q24 81 20 77Z' fill='url(#g1)'/><path d='M23 76 Q33 72 44 73 Q54 72 61 76' stroke='#4a1604' stroke-width='1.4' fill='none' opacity='0.35' stroke-linecap='round'/><path d='M25 79 Q35 76 44 77 Q54 76 62 79' stroke='#4a1604' stroke-width='0.9' fill='none' opacity='0.28' stroke-linecap='round'/><path d='M24 75 Q33 73 43 74' stroke='#c05828' stroke-width='0.8' fill='none' opacity='0.45'/><path d='M30 73 Q40 71 52 72' stroke='#b85020' stroke-width='0.8' fill='none' opacity='0.38'/><path d='M46 71 Q54 70 61 73' stroke='#c05828' stroke-width='0.8' fill='none' opacity='0.38'/><path d='M24 74 Q31 71 39 73' stroke='#f8c090' stroke-width='3' fill='none' opacity='0.3' stroke-linecap='round'/><ellipse cx='28' cy='73' rx='5' ry='2' fill='#ffe8c8' opacity='0.28'/><ellipse cx='60' cy='77' rx='20' ry='3.5' fill='#3a1004' opacity='0.2'/><path d='M38 74 Q46 62 63 62 Q76 62 80 72 Q77 78 63 79 Q48 80 38 74Z' fill='#6a2808'/><path d='M39 73 Q47 61 63 61 Q75 61 79 71 Q76 77 63 78 Q49 79 39 73Z' fill='#9a3c18'/><path d='M40 72 Q46 59 62 59 Q73 58 77 68 Q77 74 70 76 Q62 78 53 77 Q45 77 40 72Z' fill='url(#g2)'/><path d='M43 70 Q52 65 63 65 Q70 64 75 68' stroke='#4a1604' stroke-width='1.4' fill='none' opacity='0.35' stroke-linecap='round'/><path d='M44 73 Q54 70 64 70 Q71 70 76 73' stroke='#4a1604' stroke-width='0.9' fill='none' opacity='0.28' stroke-linecap='round'/><path d='M44 70 Q54 67 63 68' stroke='#c05828' stroke-width='0.8' fill='none' opacity='0.42'/><path d='M48 67 Q58 64 67 65' stroke='#b84e20' stroke-width='0.8' fill='none' opacity='0.36'/><path d='M57 63 Q65 62 72 65' stroke='#c05828' stroke-width='0.8' fill='none' opacity='0.36'/><path d='M44 69 Q52 65 62 67' stroke='#f8c090' stroke-width='3' fill='none' opacity='0.3' stroke-linecap='round'/><ellipse cx='50' cy='66' rx='6' ry='2' fill='#ffe8c8' opacity='0.26'/><path d='M51 78 Q54 81 52 85' stroke='#7a2e08' stroke-width='1.4' fill='none' opacity='0.35' stroke-linecap='round'/><path d='M43 79 Q41 82 43 85' stroke='#8a3810' stroke-width='1' fill='none' opacity='0.25' stroke-linecap='round'/><path d='M25 62 Q34 58 45 61' stroke='#3a6c18' stroke-width='2.5' fill='none' stroke-linecap='round'/><path d='M28 59.5 Q38 55 50 58' stroke='#4e8224' stroke-width='2' fill='none' stroke-linecap='round'/><path d='M56 60 Q64 56 74 59' stroke='#3a6c18' stroke-width='2.2' fill='none' stroke-linecap='round'/><path d='M59 57.5 Q67 54 77 57' stroke='#4e8224' stroke-width='1.6' fill='none' stroke-linecap='round'/><line x1='36' y1='59' x2='37' y2='61.5' stroke='#2a5010' stroke-width='0.9' opacity='0.5'/><line x1='43' y1='58' x2='44' y2='60.5' stroke='#2a5010' stroke-width='0.9' opacity='0.5'/><line x1='65' y1='58' x2='66' y2='60.5' stroke='#2a5010' stroke-width='0.9' opacity='0.5'/><ellipse cx='38' cy='72' rx='1.6' ry='1.1' fill='#e4c870' transform='rotate(-28 38 72)'/><ellipse cx='47' cy='70' rx='1.6' ry='1.05' fill='#d8bc60' transform='rotate(12 47 70)'/><ellipse cx='57' cy='73' rx='1.4' ry='1' fill='#e4c870' transform='rotate(-12 57 73)'/><ellipse cx='43' cy='79' rx='1.5' ry='0.95' fill='#d8bc60' transform='rotate(30 43 79)'/><ellipse cx='56' cy='77' rx='1.4' ry='0.95' fill='#e4c870' transform='rotate(-6 56 77)'/><ellipse cx='66' cy='69' rx='1.3' ry='0.9' fill='#d8bc60' transform='rotate(20 66 69)'/><ellipse cx='30' cy='76' rx='1.3' ry='0.9' fill='#e4c870' transform='rotate(-18 30 76)'/><ellipse cx='70' cy='73' rx='1.2' ry='0.85' fill='#d8bc60' transform='rotate(8 70 73)'/><path d='M28 50 Q25 43 27 36 Q29 30 27 23' stroke='#bab6ac' stroke-width='1.8' fill='none' stroke-linecap='round' opacity='0.38'/><path d='M50 48 Q47 41 50 34 Q53 27 50 21' stroke='#bab6ac' stroke-width='1.8' fill='none' stroke-linecap='round' opacity='0.38'/><path d='M72 50 Q75 43 73 36 Q71 29 73 22' stroke='#bab6ac' stroke-width='1.8' fill='none' stroke-linecap='round' opacity='0.38'/><path d='M39 49 Q37 43 39 37' stroke='#c8c5bc' stroke-width='1.1' fill='none' stroke-linecap='round' opacity='0.22'/><path d='M61 49 Q63 43 61 37' stroke='#c8c5bc' stroke-width='1.1' fill='none' stroke-linecap='round' opacity='0.22'/></svg>
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
