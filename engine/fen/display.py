"""FEN 显示函数（ASCII、中文、HTML）"""

from __future__ import annotations

import json

from engine.fen.types import COL_TO_CHAR

# 符号映射（用于 markdown/网页显示）
PIECE_SYMBOLS = {
    # 红方（大写）
    "K": "♔",  # 帅
    "A": "✚",  # 仕
    "E": "♗",  # 相
    "H": "♘",  # 马
    "R": "♖",  # 车
    "C": "⊕",  # 炮
    "P": "♙",  # 兵
    "X": "▣",  # 红暗子
    # 黑方（小写）
    "k": "♚",  # 将
    "a": "✜",  # 士
    "e": "♝",  # 象
    "h": "♞",  # 马
    "r": "♜",  # 车
    "c": "⊖",  # 炮
    "p": "♟",  # 卒
    "x": "▣",  # 黑暗子
}

# 中文符号映射（用于终端显示）
PIECE_SYMBOLS_CN = {
    # 红方（大写）
    "K": "帅",
    "A": "仕",
    "E": "相",
    "H": "马",
    "R": "车",
    "C": "炮",
    "P": "兵",
    "X": "暗",
    # 黑方（小写）
    "k": "将",
    "a": "士",
    "e": "象",
    "h": "馬",
    "r": "車",
    "c": "砲",
    "p": "卒",
    "x": "闇",
}

EMPTY_SYMBOL = "·"


def _parse_captured_for_canvas(captured_str: str, viewer: str) -> dict:
    """解析被吃子字符串为 canvas 显示数据

    被吃子格式：红方被吃:黑方被吃
    - 大写字母 = 明子被吃（双方都能看到）
    - 小写字母 = 暗子被吃，吃的人知道身份
    - ? = 暗子被吃，不知道身份

    显示规则（viewer 视角）：
    - 我吃对方的暗子 → 我能看到身份（显示实际棋子+暗标记）
    - 对方吃我的暗子 → 对方能看到，我看不到（显示"暗"）
    - 明子被吃 → 都能看到（正常显示）

    Args:
        captured_str: 如 "RC:pa" 或 "-:-"
        viewer: "red" 或 "black"

    Returns:
        {"red": [...], "black": [...]} 其中每项是 {"text": str, "isHidden": bool}
    """
    if captured_str == "-:-":
        return {"red": [], "black": []}

    parts = captured_str.split(":")
    red_captured_str = parts[0] if parts[0] != "-" else ""
    black_captured_str = parts[1] if len(parts) > 1 and parts[1] != "-" else ""

    def parse_side(captured: str, captured_color: str) -> list[dict]:
        """解析一方被吃的子

        Args:
            captured: 被吃子字符串，如 "RCp"
            captured_color: 被吃子的颜色 "red" 或 "black"
        """
        result = []
        # 谁吃的这个子？是对方吃的
        eater = "black" if captured_color == "red" else "red"

        for char in captured:
            if char == "?":
                # 暗子被吃，身份未知
                # 如果 viewer 是吃的人，不应该出现 ?（应该知道身份）
                # 如果 viewer 是被吃的人，显示"暗"
                result.append({"text": "暗", "isHidden": True, "isUnknown": True})
            elif char.isupper():
                # 大写 = 明子被吃，都能看到
                text = PIECE_SYMBOLS_CN.get(
                    char.lower() if captured_color == "black" else char, char
                )
                result.append({"text": text, "isHidden": False, "isUnknown": False})
            else:
                # 小写 = 暗子被吃，吃的人知道身份
                # 原始棋子字符：红方大写，黑方小写
                original_char = char.upper() if captured_color == "red" else char
                text = PIECE_SYMBOLS_CN.get(original_char, char)

                if viewer == eater:
                    # 我是吃的人，我能看到实际身份
                    result.append({"text": text, "isHidden": True, "isUnknown": False})
                else:
                    # 我是被吃的人，对方知道但我不知道
                    result.append({"text": "暗", "isHidden": True, "isUnknown": True})

        return result

    return {
        "red": parse_side(red_captured_str, "red"),
        "black": parse_side(black_captured_str, "black"),
    }


def fen_to_ascii(fen: str) -> str:
    """将 FEN 转换为 ASCII 棋盘图（符号版，适合 markdown）

    Args:
        fen: FEN 字符串

    Returns:
        ASCII 棋盘字符串
    """
    parts = fen.split()
    if not parts:
        return "Invalid FEN"

    board_str = parts[0]
    rows = board_str.split("/")

    lines = []
    for row_idx, row in enumerate(rows):
        row_num = 9 - row_idx
        line = [f"{row_num} "]
        col = 0

        for char in row:
            if char.isdigit():
                for _ in range(int(char)):
                    line.append(EMPTY_SYMBOL)
                    col += 1
            elif char in PIECE_SYMBOLS:
                line.append(PIECE_SYMBOLS[char])
                col += 1
            else:
                line.append("?")
                col += 1

        lines.append(" ".join(line))

    lines.append("   a b c d e f g h i")
    return "\n".join(lines)


def fen_to_ascii_cn(fen: str) -> str:
    """将 FEN 转换为 ASCII 棋盘图（中文版，适合终端）

    Args:
        fen: FEN 字符串

    Returns:
        ASCII 棋盘字符串
    """
    parts = fen.split()
    if not parts:
        return "Invalid FEN"

    board_str = parts[0]
    rows = board_str.split("/")

    lines = []
    for row_idx, row in enumerate(rows):
        row_num = 9 - row_idx
        line = f"{row_num} "

        for char in row:
            if char.isdigit():
                line += "十 " * int(char)
            elif char in PIECE_SYMBOLS_CN:
                line += PIECE_SYMBOLS_CN[char] + " "
            else:
                line += "? "

        lines.append(line.rstrip())

    lines.append("  0  1  2  3  4  5  6  7  8")
    return "\n".join(lines)


def fen_to_canvas_html(fen: str, arrow: str | None = None, viewer: str = "red") -> str:
    """将 FEN 转换为 Canvas 棋盘的 HTML 代码

    50% 缩放版本，适合嵌入页面。可选绘制最佳走法箭头。
    包含被吃子显示区域。

    Args:
        fen: FEN 字符串
        arrow: 可选，走法字符串如 "a0a1" 或 "+e2e3"。如果有则绘制箭头
        viewer: 视角 "red" 或 "black"，用于确定暗子显示

    Returns:
        HTML 字符串，可用于 st.components.v1.html() 渲染
    """
    parts = fen.split()
    board_str = parts[0]
    captured_str = parts[1] if len(parts) > 1 else "-:-"

    pieces = []
    rows = board_str.split("/")
    for row_idx, row in enumerate(rows):
        col = 0
        for char in row:
            if char.isdigit():
                col += int(char)
            else:
                pieces.append(
                    {
                        "x": col,
                        "y": row_idx,
                        "text": PIECE_SYMBOLS_CN.get(char, char),
                        "isRed": char.isupper(),
                        "char": char,
                    }
                )
                col += 1

    pieces_json = json.dumps(pieces)

    # 解析被吃子
    captured_data = _parse_captured_for_canvas(captured_str, viewer)
    captured_json = json.dumps(captured_data)

    # 解析箭头走法
    arrow_data = "null"
    if arrow:
        # 移除 '+' 前缀和 '=X' 后缀
        arrow_clean = arrow.lstrip("+").split("=")[0]
        if len(arrow_clean) >= 4:
            from_col = COL_TO_CHAR.index(arrow_clean[0]) if arrow_clean[0] in COL_TO_CHAR else 0
            from_row = 9 - int(arrow_clean[1])  # FEN row 转 canvas row
            to_col = COL_TO_CHAR.index(arrow_clean[2]) if arrow_clean[2] in COL_TO_CHAR else 0
            to_row = 9 - int(arrow_clean[3])
            arrow_data = json.dumps(
                {"fromCol": from_col, "fromRow": from_row, "toCol": to_col, "toRow": to_row}
            )

    # 50% 缩放: cellSize 40->20, margin 30->18, pieceRadius 16->8
    # 增加高度容纳被吃子显示区域（+44px for 2 rows）
    html = f"""
    <canvas id="interactiveBoard" style="width:196px;height:260px;"></canvas>
    <script>
    (function() {{
        const canvas = document.getElementById('interactiveBoard');
        const ctx = canvas.getContext('2d');
        const cellSize = 20;
        const margin = 18;
        const pieceRadius = 8;
        const capturedRadius = 7;
        const pieces = {pieces_json};
        const arrowData = {arrow_data};
        const captured = {captured_json};
        const colLabels = 'abcdefghi';
        const rowLabels = '9876543210';

        const dpr = window.devicePixelRatio || 1;
        const cssWidth = 196;
        const cssHeight = 260;
        const boardHeight = 216;
        canvas.width = cssWidth * dpr;
        canvas.height = cssHeight * dpr;
        ctx.scale(dpr, dpr);

        function draw() {{
            // 背景
            ctx.fillStyle = '#F5DEB3';
            ctx.fillRect(0, 0, cssWidth, boardHeight);
            // 被吃子区域背景（稍深一点）
            ctx.fillStyle = '#E8D4A8';
            ctx.fillRect(0, boardHeight, cssWidth, cssHeight - boardHeight);

            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 1;
            ctx.strokeRect(margin, margin, 8 * cellSize, 9 * cellSize);

            ctx.fillStyle = '#8B4513';
            ctx.font = 'bold 8px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            for (let i = 0; i < 9; i++) {{
                ctx.fillText(colLabels[i], margin + i * cellSize, 7);
                ctx.fillText(colLabels[i], margin + i * cellSize, boardHeight - 5);
            }}
            for (let i = 0; i < 10; i++) {{
                ctx.fillText(rowLabels[i], 7, margin + i * cellSize);
                ctx.fillText(rowLabels[i], cssWidth - 7, margin + i * cellSize);
            }}

            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 0.5;
            for (let i = 0; i < 10; i++) {{
                ctx.beginPath();
                ctx.moveTo(margin, margin + i * cellSize);
                ctx.lineTo(margin + 8 * cellSize, margin + i * cellSize);
                ctx.stroke();
            }}
            for (let j = 0; j < 9; j++) {{
                ctx.beginPath();
                ctx.moveTo(margin + j * cellSize, margin);
                ctx.lineTo(margin + j * cellSize, margin + 4 * cellSize);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(margin + j * cellSize, margin + 5 * cellSize);
                ctx.lineTo(margin + j * cellSize, margin + 9 * cellSize);
                ctx.stroke();
            }}

            [[3,0,5,2],[5,0,3,2],[3,7,5,9],[5,7,3,9]].forEach(([x1,y1,x2,y2]) => {{
                ctx.beginPath();
                ctx.moveTo(margin + x1 * cellSize, margin + y1 * cellSize);
                ctx.lineTo(margin + x2 * cellSize, margin + y2 * cellSize);
                ctx.stroke();
            }});

            function drawStar(cx, cy) {{
                const gap = 1, size = 2;
                ctx.beginPath();
                if (cx > margin) {{
                    ctx.moveTo(cx - gap, cy - gap - size);
                    ctx.lineTo(cx - gap, cy - gap);
                    ctx.lineTo(cx - gap - size, cy - gap);
                    ctx.moveTo(cx - gap, cy + gap + size);
                    ctx.lineTo(cx - gap, cy + gap);
                    ctx.lineTo(cx - gap - size, cy + gap);
                }}
                if (cx < margin + 8 * cellSize) {{
                    ctx.moveTo(cx + gap, cy - gap - size);
                    ctx.lineTo(cx + gap, cy - gap);
                    ctx.lineTo(cx + gap + size, cy - gap);
                    ctx.moveTo(cx + gap, cy + gap + size);
                    ctx.lineTo(cx + gap, cy + gap);
                    ctx.lineTo(cx + gap + size, cy + gap);
                }}
                ctx.stroke();
            }}
            [1, 7].forEach(col => [2, 7].forEach(row => drawStar(margin + col * cellSize, margin + row * cellSize)));
            [0, 2, 4, 6, 8].forEach(col => [3, 6].forEach(row => drawStar(margin + col * cellSize, margin + row * cellSize)));

            // 绘制箭头
            function drawArrow() {{
                if (!arrowData) return;
                const x1 = margin + arrowData.fromCol * cellSize;
                const y1 = margin + arrowData.fromRow * cellSize;
                const x2 = margin + arrowData.toCol * cellSize;
                const y2 = margin + arrowData.toRow * cellSize;

                const arrowColor = 'rgba(34, 139, 34, 0.9)';
                ctx.strokeStyle = arrowColor;
                ctx.fillStyle = arrowColor;
                ctx.lineWidth = 4;
                ctx.lineCap = 'round';
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();

                const angle = Math.atan2(y2 - y1, x2 - x1);
                const headLen = 10;
                ctx.beginPath();
                ctx.moveTo(x2, y2);
                ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI/5),
                           y2 - headLen * Math.sin(angle - Math.PI/5));
                ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI/5),
                           y2 - headLen * Math.sin(angle + Math.PI/5));
                ctx.closePath();
                ctx.fill();
            }}

            // 绘制棋子
            pieces.forEach(p => {{
                const x = margin + p.x * cellSize;
                const y = margin + p.y * cellSize;
                const color = p.isRed ? '#DC143C' : '#2F4F4F';

                ctx.beginPath();
                ctx.arc(x + 1, y + 1, pieceRadius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(0,0,0,0.2)';
                ctx.fill();

                ctx.beginPath();
                ctx.arc(x, y, pieceRadius, 0, Math.PI * 2);
                ctx.fillStyle = '#FFFAF0';
                ctx.fill();
                ctx.strokeStyle = color;
                ctx.lineWidth = 1;
                ctx.stroke();

                ctx.fillStyle = color;
                ctx.font = 'bold 7px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(p.text, x, y);
            }});

            drawArrow();

            // 绘制被吃子区域（两行：上面吃的，下面失的）
            function drawCaptured() {{
                const y1 = boardHeight + 14;  // 第一行：吃（红方吃黑方）
                const y2 = boardHeight + 34;  // 第二行：失（黑方吃红方）
                const spacing = 16;  // 棋子间距
                const fontSize = 6;

                // 第一行：红方吃的黑子
                ctx.font = 'bold 7px sans-serif';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#2F4F4F';
                ctx.fillText('吃:', 4, y1);

                let x = 22;
                captured.black.forEach(p => {{
                    ctx.beginPath();
                    ctx.arc(x, y1, capturedRadius, 0, Math.PI * 2);
                    ctx.fillStyle = p.isHidden ? 'rgba(255,250,240,0.6)' : '#FFFAF0';
                    ctx.fill();
                    if (p.isHidden) {{
                        ctx.setLineDash([2, 2]);
                    }}
                    ctx.strokeStyle = '#2F4F4F';
                    ctx.lineWidth = 1;
                    ctx.stroke();
                    ctx.setLineDash([]);

                    ctx.fillStyle = p.isUnknown ? '#888' : '#2F4F4F';
                    ctx.font = `bold ${{fontSize}}px sans-serif`;
                    ctx.textAlign = 'center';
                    ctx.fillText(p.text, x, y1);
                    x += spacing;
                }});

                // 第二行：红方失的子（被黑方吃）
                ctx.font = 'bold 7px sans-serif';
                ctx.textAlign = 'left';
                ctx.fillStyle = '#DC143C';
                ctx.fillText('失:', 4, y2);

                x = 22;
                captured.red.forEach(p => {{
                    ctx.beginPath();
                    ctx.arc(x, y2, capturedRadius, 0, Math.PI * 2);
                    ctx.fillStyle = p.isHidden ? 'rgba(255,250,240,0.6)' : '#FFFAF0';
                    ctx.fill();
                    if (p.isHidden) {{
                        ctx.setLineDash([2, 2]);
                    }}
                    ctx.strokeStyle = '#DC143C';
                    ctx.lineWidth = 1;
                    ctx.stroke();
                    ctx.setLineDash([]);

                    ctx.fillStyle = p.isUnknown ? '#888' : '#DC143C';
                    ctx.font = `bold ${{fontSize}}px sans-serif`;
                    ctx.textAlign = 'center';
                    ctx.fillText(p.text, x, y2);
                    x += spacing;
                }});
            }}

            drawCaptured();
        }}

        draw();
    }})();
    </script>
    """
    return html
