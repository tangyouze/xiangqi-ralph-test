// 棋盘组件

import { useCallback, useMemo } from 'react';
import type { GameState, Move, Piece, Position } from '../types';
import { PIECE_NAMES } from '../types';
import './Board.css';

interface BoardProps {
  gameState: GameState;
  selectedPosition: Position | null;
  onSelectPosition: (pos: Position | null) => void;
  onMove: (move: Move) => void;
}

export function Board({ gameState, selectedPosition, onSelectPosition, onMove }: BoardProps) {
  const { pieces, legal_moves, current_turn } = gameState;

  // 构建棋盘位置到棋子的映射
  const pieceMap = useMemo(() => {
    const map = new Map<string, Piece>();
    pieces.forEach(piece => {
      map.set(`${piece.position.row}-${piece.position.col}`, piece);
    });
    return map;
  }, [pieces]);

  // 获取选中棋子的合法目标位置
  const legalTargets = useMemo(() => {
    if (!selectedPosition) return new Set<string>();
    const targets = new Set<string>();
    legal_moves
      .filter(m => m.from.row === selectedPosition.row && m.from.col === selectedPosition.col)
      .forEach(m => targets.add(`${m.to.row}-${m.to.col}`));
    return targets;
  }, [selectedPosition, legal_moves]);

  const handleCellClick = useCallback((row: number, col: number) => {
    const pos = { row, col };
    const posKey = `${row}-${col}`;
    const piece = pieceMap.get(posKey);

    // 如果已选中棋子，且点击的是合法目标位置
    if (selectedPosition && legalTargets.has(posKey)) {
      onMove({ from: selectedPosition, to: pos });
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
  }, [pieceMap, selectedPosition, legalTargets, current_turn, onMove, onSelectPosition]);

  // 渲染棋盘
  const renderBoard = () => {
    const rows = [];

    // 从上到下渲染（row 9 在最上面）
    for (let row = 9; row >= 0; row--) {
      const cells = [];
      for (let col = 0; col < 9; col++) {
        const posKey = `${row}-${col}`;
        const piece = pieceMap.get(posKey);
        const isSelected = selectedPosition?.row === row && selectedPosition?.col === col;
        const isLegalTarget = legalTargets.has(posKey);

        cells.push(
          <div
            key={posKey}
            className={`cell ${isSelected ? 'selected' : ''} ${isLegalTarget ? 'legal-target' : ''}`}
            onClick={() => handleCellClick(row, col)}
          >
            {piece && (
              <div className={`piece ${piece.color}`}>
                {PIECE_NAMES[piece.type][piece.color]}
              </div>
            )}
            {isLegalTarget && !piece && <div className="target-indicator" />}
          </div>
        );
      }
      rows.push(
        <div key={row} className="row">
          {cells}
        </div>
      );
    }
    return rows;
  };

  return (
    <div className="board-container">
      <div className="board">
        {renderBoard()}
        {/* 楚河汉界 */}
        <div className="river">
          <span className="river-text black-side">楚 河</span>
          <span className="river-text red-side">汉 界</span>
        </div>
      </div>
    </div>
  );
}
