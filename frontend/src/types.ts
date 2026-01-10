// 游戏类型定义

export type Color = 'red' | 'black';
export type PieceType = 'king' | 'advisor' | 'elephant' | 'horse' | 'rook' | 'cannon' | 'pawn';
export type GameResult = 'ongoing' | 'red_win' | 'black_win' | 'draw';
export type GameMode = 'human_vs_human' | 'human_vs_ai' | 'ai_vs_ai';
export type AILevel = 'random' | 'easy' | 'medium' | 'hard' | 'expert';
export type AIStrategyType = 'random' | 'greedy' | 'defensive' | 'aggressive' | 'minimax';

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

// 创建游戏请求
export interface CreateGameOptions {
  mode: GameMode;
  ai_level?: AILevel;
  ai_color?: string;
  // 高级设置
  ai_strategy?: AIStrategyType;
  search_depth?: number;
  // AI vs AI 设置
  red_ai_strategy?: AIStrategyType;
  red_search_depth?: number;
  black_ai_strategy?: AIStrategyType;
  black_search_depth?: number;
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

// AI 策略描述
export const AI_STRATEGY_DESCRIPTIONS: Record<AIStrategyType, string> = {
  random: 'Random - picks random legal moves',
  greedy: 'Greedy - picks best move for current turn',
  defensive: 'Defensive - considers counter-attacks',
  aggressive: 'Aggressive - prioritizes captures',
  minimax: 'Minimax - deep search AI',
};

// AI 等级描述
export const AI_LEVEL_DESCRIPTIONS: Record<AILevel, string> = {
  random: 'Random (weakest)',
  easy: 'Easy (greedy)',
  medium: 'Medium (defensive)',
  hard: 'Hard (minimax depth 3)',
  expert: 'Expert (minimax depth 4)',
};
