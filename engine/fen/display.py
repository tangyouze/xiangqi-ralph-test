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


def fen_to_canvas_html(fen: str, arrow: str | None = None) -> str:
    """将 FEN 转换为 Canvas 棋盘的 HTML 代码

    50% 缩放版本，适合嵌入页面。可选绘制最佳走法箭头。

    Args:
        fen: FEN 字符串
        arrow: 可选，走法字符串如 "a0a1" 或 "+e2e3"。如果有则绘制箭头

    Returns:
        HTML 字符串，可用于 st.components.v1.html() 渲染
    """
    board_str = fen.split()[0]

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
    html = f"""
    <canvas id="interactiveBoard" style="width:196px;height:216px;"></canvas>
    <script>
    (function() {{
        const canvas = document.getElementById('interactiveBoard');
        const ctx = canvas.getContext('2d');
        const cellSize = 20;
        const margin = 18;
        const pieceRadius = 8;
        const pieces = {pieces_json};
        const arrowData = {arrow_data};
        const colLabels = 'abcdefghi';
        const rowLabels = '9876543210';

        const dpr = window.devicePixelRatio || 1;
        const cssWidth = 196;
        const cssHeight = 216;
        canvas.width = cssWidth * dpr;
        canvas.height = cssHeight * dpr;
        ctx.scale(dpr, dpr);

        function draw() {{
            ctx.fillStyle = '#F5DEB3';
            ctx.fillRect(0, 0, cssWidth, cssHeight);
            ctx.strokeStyle = '#8B4513';
            ctx.lineWidth = 1;
            ctx.strokeRect(margin, margin, 8 * cellSize, 9 * cellSize);

            ctx.fillStyle = '#8B4513';
            ctx.font = 'bold 8px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            for (let i = 0; i < 9; i++) {{
                ctx.fillText(colLabels[i], margin + i * cellSize, 7);
                ctx.fillText(colLabels[i], margin + i * cellSize, cssHeight - 5);
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

            // 绘制箭头（在棋子之后，这样箭头在上面更醒目）
            function drawArrow() {{
                if (!arrowData) return;
                const x1 = margin + arrowData.fromCol * cellSize;
                const y1 = margin + arrowData.fromRow * cellSize;
                const x2 = margin + arrowData.toCol * cellSize;
                const y2 = margin + arrowData.toRow * cellSize;

                const arrowColor = 'rgba(34, 139, 34, 0.9)';  // 森林绿

                // 箭头线条
                ctx.strokeStyle = arrowColor;
                ctx.fillStyle = arrowColor;
                ctx.lineWidth = 4;
                ctx.lineCap = 'round';
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();

                // 箭头头部
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

                // 阴影
                ctx.beginPath();
                ctx.arc(x + 1, y + 1, pieceRadius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(0,0,0,0.2)';
                ctx.fill();

                // 棋子底色
                ctx.beginPath();
                ctx.arc(x, y, pieceRadius, 0, Math.PI * 2);
                ctx.fillStyle = '#FFFAF0';
                ctx.fill();
                ctx.strokeStyle = color;
                ctx.lineWidth = 1;
                ctx.stroke();

                // 棋子文字
                ctx.fillStyle = color;
                ctx.font = 'bold 7px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(p.text, x, y);
            }});

            // 在棋子上方绘制箭头
            drawArrow();
        }}

        draw();
    }})();
    </script>
    """
    return html
