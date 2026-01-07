#!/usr/bin/env python3
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request


WORKFLOW_TEMPLATE = {
    "8": {
        "inputs": {"samples": ["127", 0], "vae": ["10", 0]},
        "class_type": "VAEDecode",
        "_meta": {"title": "VAEデコード"},
    },
    "10": {
        "inputs": {"vae_name": "hunyuanvideo15_vae_fp16.safetensors"},
        "class_type": "VAELoader",
        "_meta": {"title": "VAEを読み込む"},
    },
    "11": {
        "inputs": {
            "clip_name1": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
            "clip_name2": "byt5_small_glyphxl_fp16.safetensors",
            "type": "hunyuan_video_15",
            "device": "default",
        },
        "class_type": "DualCLIPLoader",
        "_meta": {"title": "デュアルCLIPを読み込む"},
    },
    "12": {
        "inputs": {"unet_name": "hunyuanvideo1.5_720p_t2v_fp16.safetensors", "weight_dtype": "default"},
        "class_type": "UNETLoader",
        "_meta": {"title": "拡散モデルを読み込む"},
    },
    "44": {
        "inputs": {
            "text": "A paper airplane released from the top of a skyscraper, gliding through urban canyons, crossing traffic, flying over streets, spiraling upward between buildings. The camera follows the paper airplane's perspective, shooting cityscape in first-person POV, finally flying toward the sunset, disappearing in golden light. Creative camera movement, free perspective, dreamlike colors.",
            "clip": ["11", 0],
        },
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Positive Prompt)"},
    },
    "93": {
        "inputs": {"text": "", "clip": ["11", 0]},
        "class_type": "CLIPTextEncode",
        "_meta": {"title": "CLIP Text Encode (Negative Prompt)"},
    },
    "101": {
        "inputs": {"fps": 24, "images": ["8", 0]},
        "class_type": "CreateVideo",
        "_meta": {"title": "動画を作成"},
    },
    "102": {
        "inputs": {
            "filename_prefix": "video/hunyuan_video_1.5",
            "format": "auto",
            "codec": "h264",
            "video": ["101", 0],
        },
        "class_type": "SaveVideo",
        "_meta": {"title": "ビデオを保存"},
    },
    "124": {
        "inputs": {"width": 1280, "height": 720, "length": 121, "batch_size": 1},
        "class_type": "EmptyHunyuanVideo15Latent",
        "_meta": {"title": "Empty HunyuanVideo 1.5 Latent"},
    },
    "127": {
        "inputs": {
            "noise": ["129", 0],
            "guider": ["131", 0],
            "sampler": ["130", 0],
            "sigmas": ["128", 0],
            "latent_image": ["124", 0],
        },
        "class_type": "SamplerCustomAdvanced",
        "_meta": {"title": "カスタムサンプラー（高度）"},
    },
    "128": {
        "inputs": {"scheduler": "simple", "steps": 20, "denoise": 1, "model": ["12", 0]},
        "class_type": "BasicScheduler",
        "_meta": {"title": "基本スケジューラー"},
    },
    "129": {
        "inputs": {"noise_seed": 887963123424675},
        "class_type": "RandomNoise",
        "_meta": {"title": "ランダムノイズ"},
    },
    "130": {
        "inputs": {"sampler_name": "euler"},
        "class_type": "KSamplerSelect",
        "_meta": {"title": "Kサンプラー選択"},
    },
    "131": {
        "inputs": {"cfg": 6, "model": ["132", 0], "positive": ["44", 0], "negative": ["93", 0]},
        "class_type": "CFGGuider",
        "_meta": {"title": "CFGガイダー"},
    },
    "132": {
        "inputs": {"shift": 7, "model": ["12", 0]},
        "class_type": "ModelSamplingSD3",
        "_meta": {"title": "モデルサンプリングSD3"},
    },
}


def http_json(url, method="GET", data=None):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=body, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url, output_path):
    with urllib.request.urlopen(url) as resp, open(output_path, "wb") as f:
        f.write(resp.read())


def build_prompt(prompt_text, negative_text, seed, filename_prefix):
    workflow = json.loads(json.dumps(WORKFLOW_TEMPLATE))
    workflow["44"]["inputs"]["text"] = prompt_text
    workflow["93"]["inputs"]["text"] = negative_text
    workflow["129"]["inputs"]["noise_seed"] = seed
    workflow["102"]["inputs"]["filename_prefix"] = filename_prefix
    return {"prompt": workflow}


def find_video_info(history_payload):
    outputs = history_payload.get("outputs", {})
    for node_data in outputs.values():
        if "videos" in node_data and node_data["videos"]:
            return node_data["videos"][0]
        if "video" in node_data and node_data["video"]:
            return node_data["video"]
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate video via ComfyUI API.")
    parser.add_argument("--host", default="http://192.168.1.3:8188", help="ComfyUI base URL")
    parser.add_argument("--prompt", required=True, help="Positive prompt text")
    parser.add_argument("--negative", default="", help="Negative prompt text")
    parser.add_argument("--out", default="comfy_video", help="Output file prefix (without index/extension)")
    parser.add_argument("--timeout", type=int, default=21600, help="Timeout seconds")
    parser.add_argument("--poll", type=int, default=5, help="Poll interval seconds")
    parser.add_argument("--count", type=int, default=5, help="Number of videos to generate")
    parser.add_argument("--seed", type=int, default=None, help="Base seed (incremented per video)")
    args = parser.parse_args()

    base_seed = args.seed if args.seed is not None else int(time.time())
    for index in range(1, args.count + 1):
        seed = base_seed + index - 1
        filename_prefix = f"video/hunyuan_video_1.5_{seed}"
        payload = build_prompt(args.prompt, args.negative, seed, filename_prefix)
        prompt_resp = http_json(f"{args.host}/prompt", method="POST", data=payload)
        prompt_id = prompt_resp.get("prompt_id")
        if not prompt_id:
            print(f"Failed to start prompt: {prompt_resp}", file=sys.stderr)
            return 1

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            history = http_json(f"{args.host}/history/{prompt_id}")
            entry = history.get(prompt_id)
            if entry and entry.get("status", {}).get("completed"):
                video_info = find_video_info(entry)
                if not video_info:
                    print("Completed but no video info found in outputs.", file=sys.stderr)
                    return 2
                query = urllib.parse.urlencode(
                    {
                        "filename": video_info.get("filename", ""),
                        "subfolder": video_info.get("subfolder", ""),
                        "type": video_info.get("type", "output"),
                    }
                )
                download_url = f"{args.host}/view?{query}"
                output_path = f"{args.out}_{index}.mp4"
                download_file(download_url, output_path)
                print(output_path)
                break
            time.sleep(args.poll)
        else:
            print("Timed out waiting for video generation.", file=sys.stderr)
            return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
