// 揭棋棋盘组件

import { useCallback, useMemo } from 'react';
import type { ReactNode } from 'react';
import type { JieqiGameState, JieqiMove, JieqiPiece, Position } from './types';
import { PIECE_NAMES, HIDDEN_PIECE_CHAR } from './types';
import './JieqiBoard.css';

interface JieqiBoardProps {
  gameState: JieqiGameState;
  selectedPosition: Position | null;
  onSelectPosition: (pos: Position | null) => void;
  onMove: (move: JieqiMove) => void;
}

// 棋盘尺寸常量
const CELL_SIZE = 64;
const BOARD_COLS = 9;
const BOARD_ROWS = 10;

export function JieqiBoard({ gameState, selectedPosition, onSelectPosition, onMove }: JieqiBoardProps) {
  const { pieces, legal_moves, current_turn } = gameState;

  // 构建棋盘位置到棋子的映射
  const pieceMap = useMemo(() => {
    const map = new Map<string, JieqiPiece>();
    pieces.forEach(piece => {
      map.set(`${piece.position.row}-${piece.position.col}`, piece);
    });
    return map;
  }, [pieces]);

  // 获取选中棋子的合法目标位置和动作类型
  const legalMoves = useMemo(() => {
    if (!selectedPosition) return new Map<string, JieqiMove>();
    const moves = new Map<string, JieqiMove>();
    legal_moves
      .filter(m => m.from_pos.row === selectedPosition.row && m.from_pos.col === selectedPosition.col)
      .forEach(m => moves.set(`${m.to_pos.row}-${m.to_pos.col}`, m));
    return moves;
  }, [selectedPosition, legal_moves]);

  const handleCellClick = useCallback((row: number, col: number) => {
    const pos = { row, col };
    const posKey = `${row}-${col}`;
    const piece = pieceMap.get(posKey);

    // 如果已选中棋子，且点击的是合法目标位置
    const legalMove = legalMoves.get(posKey);
    if (selectedPosition && legalMove) {
      onMove(legalMove);
      onSelectPosition(null);
      return;
    }

    // 如果点击的是己方棋子，选中它
    if (piece && piece.color === current_turn) {
      onSelectPosition(pos);
      return;
    }

    // 否则取消选中
    onSelectPosition(null);
  }, [pieceMap, selectedPosition, legalMoves, current_turn, onMove, onSelectPosition]);

  // 渲染棋子
  const renderPieceContent = (piece: JieqiPiece) => {
    if (piece.state === 'hidden') {
      // 暗子显示特殊字符
      return HIDDEN_PIECE_CHAR[piece.color];
    } else {
      // 明子显示真实棋子
      return piece.type ? PIECE_NAMES[piece.type][piece.color] : '?';
    }
  };

  // 渲染棋子层
  const renderPieces = () => {
    const elements: ReactNode[] = [];

    // 从上到下渲染（row 9 在最上面，这是黑方）
    for (let row = BOARD_ROWS - 1; row >= 0; row--) {
      for (let col = 0; col < BOARD_COLS; col++) {
        const posKey = `${row}-${col}`;
        const piece = pieceMap.get(posKey);
        const isSelected = selectedPosition?.row === row && selectedPosition?.col === col;
        const isLegalTarget = legalMoves.has(posKey);

        // 计算实际位置（以交叉点为中心）
        const visualRow = BOARD_ROWS - 1 - row;
        const x = col * CELL_SIZE;
        const y = visualRow * CELL_SIZE;

        elements.push(
          <div
            key={posKey}
            className={`intersection ${isSelected ? 'selected' : ''} ${isLegalTarget ? 'legal-target' : ''}`}
            style={{
              left: x,
              top: y,
            }}
            onClick={() => handleCellClick(row, col)}
          >
            {piece && (
              <div className={`piece ${piece.color} ${piece.state === 'hidden' ? 'hidden-piece' : ''}`}>
                {renderPieceContent(piece)}
              </div>
            )}
            {isLegalTarget && !piece && <div className="target-indicator" />}
          </div>
        );
      }
    }
    return elements;
  };

  // 渲染棋盘网格线（SVG）
  const renderGrid = () => {
    const width = (BOARD_COLS - 1) * CELL_SIZE;
    const height = (BOARD_ROWS - 1) * CELL_SIZE;
    const lines: ReactNode[] = [];

    // 水平线（10条）
    for (let i = 0; i < BOARD_ROWS; i++) {
      const y = i * CELL_SIZE;
      lines.push(
        <line
          key={`h-${i}`}
          x1={0}
          y1={y}
          x2={width}
          y2={y}
          stroke="#5a4a3a"
          strokeWidth="1.5"
        />
      );
    }

    // 垂直线（9条，但楚河区域只有边界线）
    for (let i = 0; i < BOARD_COLS; i++) {
      const x = i * CELL_SIZE;
      if (i === 0 || i === BOARD_COLS - 1) {
        // 边界线：完整
        lines.push(
          <line
            key={`v-${i}`}
            x1={x}
            y1={0}
            x2={x}
            y2={height}
            stroke="#5a4a3a"
            strokeWidth="1.5"
          />
        );
      } else {
        // 中间线：分上下两段（楚河汉界断开）
        const riverTop = 4 * CELL_SIZE;
        const riverBottom = 5 * CELL_SIZE;
        lines.push(
          <line
            key={`v-${i}-top`}
            x1={x}
            y1={0}
            x2={x}
            y2={riverTop}
            stroke="#5a4a3a"
            strokeWidth="1.5"
          />,
          <line
            key={`v-${i}-bottom`}
            x1={x}
            y1={riverBottom}
            x2={x}
            y2={height}
            stroke="#5a4a3a"
            strokeWidth="1.5"
          />
        );
      }
    }

    // 九宫格斜线 - 黑方（上方，row 7-9）
    const palaceTop = 0;
    const palaceLeft = 3 * CELL_SIZE;
    lines.push(
      <line
        key="palace-black-1"
        x1={palaceLeft}
        y1={palaceTop}
        x2={palaceLeft + 2 * CELL_SIZE}
        y2={palaceTop + 2 * CELL_SIZE}
        stroke="#5a4a3a"
        strokeWidth="1.5"
      />,
      <line
        key="palace-black-2"
        x1={palaceLeft + 2 * CELL_SIZE}
        y1={palaceTop}
        x2={palaceLeft}
        y2={palaceTop + 2 * CELL_SIZE}
        stroke="#5a4a3a"
        strokeWidth="1.5"
      />
    );

    // 九宫格斜线 - 红方（下方，row 0-2）
    const palaceBottom = 7 * CELL_SIZE;
    lines.push(
      <line
        key="palace-red-1"
        x1={palaceLeft}
        y1={palaceBottom}
        x2={palaceLeft + 2 * CELL_SIZE}
        y2={palaceBottom + 2 * CELL_SIZE}
        stroke="#5a4a3a"
        strokeWidth="1.5"
      />,
      <line
        key="palace-red-2"
        x1={palaceLeft + 2 * CELL_SIZE}
        y1={palaceBottom}
        x2={palaceLeft}
        y2={palaceBottom + 2 * CELL_SIZE}
        stroke="#5a4a3a"
        strokeWidth="1.5"
      />
    );

    return (
      <svg
        className="board-grid-svg"
        width={width}
        height={height}
        style={{
          position: 'absolute',
          left: CELL_SIZE / 2,
          top: CELL_SIZE / 2,
        }}
      >
        {lines}
      </svg>
    );
  };

  // 渲染星位标记
  const renderStarMarks = () => {
    // 炮位和兵位的星位
    const starPositions = [
      // 黑方炮位
      { row: 7, col: 1 },
      { row: 7, col: 7 },
      // 黑方卒位
      { row: 6, col: 0 },
      { row: 6, col: 2 },
      { row: 6, col: 4 },
      { row: 6, col: 6 },
      { row: 6, col: 8 },
      // 红方炮位
      { row: 2, col: 1 },
      { row: 2, col: 7 },
      // 红方兵位
      { row: 3, col: 0 },
      { row: 3, col: 2 },
      { row: 3, col: 4 },
      { row: 3, col: 6 },
      { row: 3, col: 8 },
    ];

    return starPositions.map(({ row, col }) => {
      const visualRow = BOARD_ROWS - 1 - row;
      const x = col * CELL_SIZE + CELL_SIZE / 2;
      const y = visualRow * CELL_SIZE + CELL_SIZE / 2;
      const isLeftEdge = col === 0;
      const isRightEdge = col === 8;

      return (
        <div
          key={`star-${row}-${col}`}
          className="star-mark"
          style={{ left: x, top: y }}
        >
          {!isLeftEdge && (
            <>
              <div className="star-corner lt" />
              <div className="star-corner lb" />
            </>
          )}
          {!isRightEdge && (
            <>
              <div className="star-corner rt" />
              <div className="star-corner rb" />
            </>
          )}
        </div>
      );
    });
  };

  return (
    <div className="board-container">
      <div
        className="board"
        style={{
          width: BOARD_COLS * CELL_SIZE,
          height: BOARD_ROWS * CELL_SIZE,
        }}
      >
        {/* 网格线 */}
        {renderGrid()}

        {/* 星位标记 */}
        {renderStarMarks()}

        {/* 楚河汉界文字 */}
        <div
          className="river-text"
          style={{
            top: 4 * CELL_SIZE + CELL_SIZE / 2,
            height: CELL_SIZE,
          }}
        >
          <span className="black-side">楚 河</span>
          <span className="red-side">漢 界</span>
        </div>

        {/* 棋子层 */}
        <div className="pieces-layer">
          {renderPieces()}
        </div>
      </div>
    </div>
  );
}
