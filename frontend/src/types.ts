// 游戏类型定义

export type Color = 'red' | 'black';
export type PieceType = 'king' | 'advisor' | 'elephant' | 'horse' | 'rook' | 'cannon' | 'pawn';
export type GameResult = 'ongoing' | 'red_win' | 'black_win' | 'draw';
export type GameMode = 'human_vs_human' | 'human_vs_ai' | 'ai_vs_ai';
export type AILevel = 'random' | 'easy' | 'medium' | 'hard';

export interface Position {
  row: number;
  col: number;
}

export interface Piece {
  type: PieceType;
  color: Color;
  position: Position;
}

export interface Move {
  from: Position;
  to: Position;
}

export interface GameState {
  game_id: string;
  mode: GameMode;
  pieces: Piece[];
  current_turn: Color;
  result: GameResult;
  is_in_check: boolean;
  legal_moves: Move[];
  move_count: number;
}

export interface MoveResponse {
  success: boolean;
  game_state: GameState | null;
  error: string | null;
  ai_move: Move | null;
}

// 棋子显示名称
export const PIECE_NAMES: Record<PieceType, Record<Color, string>> = {
  king: { red: '帅', black: '将' },
  advisor: { red: '仕', black: '士' },
  elephant: { red: '相', black: '象' },
  horse: { red: '马', black: '马' },
  rook: { red: '车', black: '车' },
  cannon: { red: '炮', black: '炮' },
  pawn: { red: '兵', black: '卒' },
};
