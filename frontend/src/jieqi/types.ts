// 揭棋游戏类型定义

export type Color = 'red' | 'black';
export type PieceType = 'king' | 'advisor' | 'elephant' | 'horse' | 'rook' | 'cannon' | 'pawn';
export type PieceState = 'hidden' | 'revealed';
export type ActionType = 'reveal_and_move' | 'move';
export type GameResult = 'ongoing' | 'red_win' | 'black_win' | 'draw';
export type GameMode = 'human_vs_human' | 'human_vs_ai' | 'ai_vs_ai';
export type AILevel = 'random';

export interface Position {
  row: number;
  col: number;
}

export interface JieqiPiece {
  color: Color;
  position: Position;
  state: PieceState;
  type?: PieceType; // 只有明子才有
}

export interface JieqiMove {
  action_type: ActionType;
  from_pos: Position;
  to_pos: Position;
}

export interface JieqiGameState {
  game_id: string;
  mode: GameMode;
  pieces: JieqiPiece[];
  current_turn: Color;
  result: GameResult;
  is_in_check: boolean;
  legal_moves: JieqiMove[];
  move_count: number;
  hidden_count: {
    red: number;
    black: number;
  };
}

export interface JieqiMoveResponse {
  success: boolean;
  game_state: JieqiGameState | null;
  error: string | null;
  ai_move: JieqiMove | null;
}

// 创建游戏请求
export interface CreateJieqiGameOptions {
  mode: GameMode;
  ai_level?: AILevel;
  ai_color?: string;
  seed?: number;
}

// 棋子显示名称
export const PIECE_NAMES: Record<PieceType, Record<Color, string>> = {
  king: { red: '帥', black: '將' },
  advisor: { red: '仕', black: '士' },
  elephant: { red: '相', black: '象' },
  horse: { red: '馬', black: '馬' },
  rook: { red: '車', black: '車' },
  cannon: { red: '炮', black: '砲' },
  pawn: { red: '兵', black: '卒' },
};

// 暗子显示
export const HIDDEN_PIECE_CHAR: Record<Color, string> = {
  red: '暗',
  black: '闇',
};
