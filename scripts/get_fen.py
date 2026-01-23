#!/usr/bin/env python3
"""
获取局面的 FEN 字符串

支持输入局面 ID（如 END0001、JIEQI）或直接返回 FEN 字符串
"""

import sys

from engine.positions import get_position


def main():
    if len(sys.argv) < 2:
        print("Usage: get_fen.py <POSITION>", file=sys.stderr)
        print("  POSITION: Position ID (e.g., END0001, JIEQI) or FEN string", file=sys.stderr)
        sys.exit(1)

    position_arg = sys.argv[1]
    pos = get_position(position_arg)

    if pos is None:
        print(f"Unknown position: {position_arg}", file=sys.stderr)
        sys.exit(1)

    # 输出 FEN 字符串（不带换行符方便 shell 使用）
    print(pos.fen, end="")


if __name__ == "__main__":
    main()
