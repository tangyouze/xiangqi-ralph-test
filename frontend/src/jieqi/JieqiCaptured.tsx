// 被吃棋子展示组件

import type { CapturedPiece, Color } from './types';
import { PIECE_NAMES, HIDDEN_PIECE_CHAR } from './types';
import './JieqiCaptured.css';

interface JieqiCapturedProps {
  capturedPieces?: {
    red: CapturedPiece[];
    black: CapturedPiece[];
  };
}

export function JieqiCaptured({ capturedPieces }: JieqiCapturedProps) {
  if (!capturedPieces) {
    return null;
  }

  const renderPiece = (piece: CapturedPiece, index: number) => {
    const pieceColor = piece.color;
    let displayChar: string;

    if (piece.was_hidden || !piece.type) {
      // 暗子显示为暗/闇
      displayChar = HIDDEN_PIECE_CHAR[pieceColor];
    } else {
      // 明子显示真实棋子
      displayChar = PIECE_NAMES[piece.type]?.[pieceColor] || '?';
    }

    return (
      <span
        key={index}
        className={`captured-piece ${pieceColor} ${piece.was_hidden ? 'was-hidden' : ''}`}
        title={piece.type ? piece.type : 'hidden piece'}
      >
        {displayChar}
      </span>
    );
  };

  const renderCapturedSection = (pieces: CapturedPiece[], capturedBy: Color) => {
    if (pieces.length === 0) {
      return <span className="no-captured">-</span>;
    }

    return (
      <div className="captured-list">
        {pieces.map((piece, index) => renderPiece(piece, index))}
      </div>
    );
  };

  return (
    <div className="jieqi-captured">
      <div className="captured-section red-captured">
        <span className="captured-label">Red captured:</span>
        {renderCapturedSection(capturedPieces.red, 'red')}
      </div>
      <div className="captured-section black-captured">
        <span className="captured-label">Black captured:</span>
        {renderCapturedSection(capturedPieces.black, 'black')}
      </div>
    </div>
  );
}
