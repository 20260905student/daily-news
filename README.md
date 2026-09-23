# 朝のニュース

世間・日米株・暗号資産・AIのニュースを日本時間の毎朝7時に向けて更新する、スマートフォン対応のニュースサイトです。Google ニュースの日本語 RSS から直近48時間の記事を取得します。Gemini API は重要度順の選定に加え、各記事の見出しと一致する Bing ニュースの配信文がある場合、その抜粋を根拠に「ポイント」と「背景・影響」を記事ごとに生成します。一致する抜粋がない場合は見出しに基づくポイントのみ表示し、未確認の背景や影響は補いません。各カードから元記事へ移動できます。

## 初回設定

1. GitHub リポジトリの **Settings → Pages → Build and deployment → Source** で **GitHub Actions** を選びます。
2. 日本語の要点を使う場合は、Google AI Studio で Gemini API キーを取得します。課金を避けたい場合は、請求先を登録していない無料枠のプロジェクトを使い、利用状況と上限を Google AI Studio で確認します。キーは GitHub リポジトリの **Settings → Secrets and variables → Actions → New repository secret** から `GEMINI_API_KEY` という名前で登録します。キーをサイトのコードに書かないでください。
3. **Actions → Daily news → Run workflow** で一度実行し、発行された Pages の URL を iPhone/iPad で開きます。Safari の共有メニューから「ホーム画面に追加」もできます。

API キー未登録や要約エラーの場合も、記事の見出しと出典を掲載します。RSS 全体が取得できない場合は処理が失敗し、前回のサイトを維持します。

## 更新と保存

定時処理は日本時間6:35に開始する設定です。7:00までの公開を目指しますが、GitHub Actions には遅延があり、時刻を保証できません。`Actions` から手動更新もできます。公開データは直近30日分だけ残し、31日目以降は削除します。同じ日に再実行すると当日分を更新します。

GitHub Pages の無料プランではリポジトリを公開にする必要があります。URL を知る人が読める設計ですが、アクセス制限はなく、URL を知らない人にも公開されます。非公開閲覧が必要なら、別途認証付きの公開先を利用してください。

GitHub と Google のサービスを利用するため、ChatGPT の有料プラン契約に依存しません。Gemini の料金・無料枠と GitHub の利用条件は変更される場合があります。

## ローカル確認

`pip install -r requirements.txt` の後に `python build.py` を実行し、`public/index.html` を生成します。実際のサイトは GitHub Pages から `/daily-news/` で表示します。
