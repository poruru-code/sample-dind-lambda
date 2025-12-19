# Gateway Application Container
# FastAPIアプリケーションのみを実行（DinD機能なし）

FROM python:3.11-slim

WORKDIR /app

# uvのインストール
RUN pip install --no-cache-dir uv

# アプリケーションコードをコピー
COPY gateway/app/ /app/gateway/app/
COPY pyproject.toml /app/

# 設定ファイルをコピー
COPY gateway/config/ /app/config/

# Python依存関係をインストール
RUN uv pip install --system --break-system-packages -e .

# データディレクトリ作成
RUN mkdir -p /logs

# 起動スクリプト
COPY gateway/start_app.sh /start_app.sh
RUN chmod +x /start_app.sh

CMD ["/start_app.sh"]
