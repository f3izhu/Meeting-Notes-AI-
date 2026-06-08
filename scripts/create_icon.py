from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (256, 256), "#1e1e2e")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((36, 36, 220, 220), radius=36, fill="#89b4fa")
    draw.rounded_rectangle((64, 74, 192, 104), radius=8, fill="#1e1e2e")
    draw.rounded_rectangle((64, 126, 178, 156), radius=8, fill="#1e1e2e")
    draw.rounded_rectangle((64, 178, 154, 198), radius=8, fill="#1e1e2e")
    image.save(ASSETS / "MeetingNotesAI.ico", sizes=[(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)])
    image.save(ASSETS / "MeetingNotesAI.png")
    print(f"Created {ASSETS / 'MeetingNotesAI.ico'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

