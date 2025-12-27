# AImovie-auto-generator

ComfyUI APIを使って、テキストプロンプトから動画を生成しダウンロードするスクリプトです。

## 使い方

```bash
python3 comfy_video_generate.py \
  --prompt "A paper airplane flying through a city at sunset" \
  --out comfy_video.mp4
```

オプション:
- `--host` ComfyUIのURL（デフォルト `http://192.168.1.3:8188`）
- `--negative` ネガティブプロンプト
- `--timeout` タイムアウト秒（デフォルト1800）
- `--poll` 進捗ポーリング間隔秒

## 前提

- ComfyUIが起動していること
- HunyuanVideo 1.5関連のモデル/ノードがセットアップ済みであること
