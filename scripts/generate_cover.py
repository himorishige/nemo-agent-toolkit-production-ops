"""Zenn Book 続編「NeMo Agent Toolkit 実践運用編」のカバー画像を生成する.

前作 (nemo-agent-toolkit-book) と同じ設計言語（NVIDIA ダーク + 緑ノードグラフ）を踏襲し、
タイトル文字列とグラフのシードのみを差し替えて続編らしさを出す.
出力サイズは Zenn 公式推奨の 500x700.

Usage:
    uv run --group tools python scripts/generate_cover.py

Pillow は dependency-groups の "tools" に登録されている.
レイアウトのバリエーションを試す場合は GRAPH_SEED を変える.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).resolve().parent.parent / "cover.png"

WIDTH = 500
HEIGHT = 700

NVIDIA_GREEN = (118, 185, 0)  # #76B900
NVIDIA_DARK = (15, 17, 18)  # #0F1112
WHITE = (255, 255, 255)
ACCENT = (174, 232, 0)  # #AEE800 明るめの緑アクセント
MUTED = (180, 200, 150)  # 緑寄りのグレー（補助テキスト）

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

GRAPH_SEED = 137  # 前作 (42) と別パターンにして続編らしさを出す
NODE_COUNT = 24  # 前作より少しだけ密度を上げる
EDGE_DISTANCE = 165  # 距離がこの値以下のペアをエッジで結ぶ


def _font(size: int, *, bold: bool = True) -> ImageFont.FreeTypeFont:
    # NotoSansCJK-Bold.ttc index=2 が日本語Boldグリフ. Regular相当はindex=0.
    return ImageFont.truetype(FONT_PATH, size=size, index=2 if bold else 0)


def _generate_nodes(rng: random.Random) -> list[tuple[float, float]]:
    """画面全体に散らすノード座標. タイトル中央領域は密度を下げる."""
    nodes: list[tuple[float, float]] = []
    margin = 30
    # タイトル中央領域 (この矩形に入ったノードは完全に除外して可読性を確保)
    title_box = (40, 180, WIDTH - 40, 540)

    attempts = 0
    while len(nodes) < NODE_COUNT and attempts < 400:
        attempts += 1
        x = rng.uniform(margin, WIDTH - margin)
        y = rng.uniform(margin + 20, HEIGHT - margin - 20)

        # タイトル領域はノードを置かない
        if title_box[0] < x < title_box[2] and title_box[1] < y < title_box[3]:
            continue

        # 既存ノードと近すぎる場合は却下
        too_close = any((x - nx) ** 2 + (y - ny) ** 2 < 55**2 for nx, ny in nodes)
        if too_close:
            continue

        nodes.append((x, y))
    return nodes


def draw_graph(base: Image.Image) -> None:
    """エージェントネットワーク風の背景グラフを薄く描画."""
    rng = random.Random(GRAPH_SEED)
    nodes = _generate_nodes(rng)

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # --- エッジ ---
    title_box = (40, 180, WIDTH - 40, 540)
    for i, (x1, y1) in enumerate(nodes):
        for x2, y2 in nodes[i + 1 :]:
            d = math.hypot(x1 - x2, y1 - y2)
            if d > EDGE_DISTANCE:
                continue
            # エッジがタイトル領域を横断する場合はスキップ（中点判定）
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if title_box[0] < mx < title_box[2] and title_box[1] < my < title_box[3]:
                continue
            # 距離が近いほど不透明度が上がる
            alpha = int(70 * (1 - d / EDGE_DISTANCE)) + 25
            draw.line(
                [(x1, y1), (x2, y2)],
                fill=(*NVIDIA_GREEN, alpha),
                width=1,
            )

    # --- ノード ---
    # 4 本柱 (Orchestration / Guardrails / Observability / Eval) を象徴して 4 つだけ強調
    highlight_indices = set(rng.sample(range(len(nodes)), k=min(4, len(nodes))))
    for i, (x, y) in enumerate(nodes):
        if i in highlight_indices:
            # ハイライト: グロー → リング → 中心
            for r, a in [(14, 35), (10, 60), (7, 110)]:
                draw.ellipse(
                    [(x - r, y - r), (x + r, y + r)],
                    fill=(*ACCENT, a),
                )
            draw.ellipse(
                [(x - 4, y - 4), (x + 4, y + 4)],
                fill=(*ACCENT, 255),
            )
        else:
            r = rng.choice([3, 4, 5])
            # 外周リング
            draw.ellipse(
                [(x - r - 2, y - r - 2), (x + r + 2, y + r + 2)],
                outline=(*NVIDIA_GREEN, 160),
                width=1,
            )
            draw.ellipse(
                [(x - r, y - r), (x + r, y + r)],
                fill=(*NVIDIA_GREEN, 180),
            )

    # 合成
    base.alpha_composite(layer)


def draw_accents(draw: ImageDraw.ImageDraw) -> None:
    """上下のアクセント帯と中央ディバイダ、コーナーマーク."""
    # 上下の細い緑帯
    draw.rectangle([(0, 0), (WIDTH, 6)], fill=NVIDIA_GREEN)
    draw.rectangle([(0, HEIGHT - 6), (WIDTH, HEIGHT)], fill=NVIDIA_GREEN)

    # 左上のコーナーマーク（鉤型）
    cx, cy = 24, 24
    arm = 18
    draw.line([(cx, cy), (cx + arm, cy)], fill=NVIDIA_GREEN, width=2)
    draw.line([(cx, cy), (cx, cy + arm)], fill=NVIDIA_GREEN, width=2)
    # 右下のコーナーマーク
    cx, cy = WIDTH - 24, HEIGHT - 24
    draw.line([(cx, cy), (cx - arm, cy)], fill=NVIDIA_GREEN, width=2)
    draw.line([(cx, cy), (cx, cy - arm)], fill=NVIDIA_GREEN, width=2)

    # 中央のディバイダ（タイトルとサブタイトルの間）
    line_w = 70
    line_y = HEIGHT - 105
    draw.rectangle(
        [((WIDTH - line_w) // 2, line_y), ((WIDTH + line_w) // 2, line_y + 3)],
        fill=ACCENT,
    )


def draw_title(draw: ImageDraw.ImageDraw) -> None:
    """タイトルを階層的に配置.

    主役は "NeMo Agent Toolkit"（2 行に分けて大きく）.
    続編は "Guardrails × Langfuse" を上段、"実践運用編" を下段に配置.
    """
    # 上段（補助）: 32pt + 26pt
    sub_top_font = _font(32)
    sub_top2_font = _font(26)
    # 主役: 58pt
    hero_font = _font(58)
    # 下段（補助）: 36pt（前作の「ハンズオン」より少し大きく、副題「実践運用編」を強調）
    bottom_font = _font(36)

    lines: list[tuple[str, ImageFont.FreeTypeFont, tuple[int, int, int], int]] = [
        ("Guardrails × Langfuse", sub_top_font, WHITE, 0),
        ("で本番運用する", sub_top2_font, MUTED, 8),
        ("NeMo Agent", hero_font, WHITE, 30),
        ("Toolkit", hero_font, WHITE, 6),
        ("実践運用編", bottom_font, WHITE, 28),
    ]

    # 合計の高さを概算して中央に寄せる
    total = 0
    heights: list[int] = []
    for text, font, _color, gap in lines:
        bbox = font.getbbox(text)
        h = bbox[3] - bbox[1]
        heights.append(h)
        total += h + gap

    y = (HEIGHT - total) // 2 - 30

    for (text, font, color, gap), h in zip(lines, heights, strict=True):
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2 - bbox[0]
        draw.text((x, y + gap - bbox[1]), text, font=font, fill=color)
        y += h + gap


def draw_subtitle(draw: ImageDraw.ImageDraw) -> None:
    """下部の小さなサブテキスト."""
    font = _font(17)
    sub = "NAT 1.6.0 × Langfuse v3 × NeMo Guardrails"
    bbox = font.getbbox(sub)
    text_w = bbox[2] - bbox[0]
    x = (WIDTH - text_w) // 2 - bbox[0]
    y = HEIGHT - 75
    draw.text((x, y - bbox[1]), sub, font=font, fill=ACCENT)


def main() -> None:
    img = Image.new("RGBA", (WIDTH, HEIGHT), (*NVIDIA_DARK, 255))

    draw_graph(img)

    draw = ImageDraw.Draw(img)
    draw_accents(draw)
    draw_title(draw)
    draw_subtitle(draw)

    img.convert("RGB").save(OUTPUT, "PNG", optimize=True)
    print(f"Saved: {OUTPUT} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
