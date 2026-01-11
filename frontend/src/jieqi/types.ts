// 揭棋游戏类型定义

export type Color = 'red' | 'black';
export type PieceType = 'king' | 'advisor' | 'elephant' | 'horse' | 'rook' | 'cannon' | 'pawn';
export type PieceState = 'hidden' | 'revealed';
export type ActionType = 'reveal_and_move' | 'move';
export type GameResult = 'ongoing' | 'red_win' | 'black_win' | 'draw';
export type GameMode = 'human_vs_human' | 'human_vs_ai' | 'ai_vs_ai';
export type AILevel = string;
export type AIStrategy = string;

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
  delay_reveal: boolean;  // 是否为延迟分配模式
}

export interface JieqiMoveResponse {
  success: boolean;
  game_state: JieqiGameState | null;
  error: string | null;
  ai_move: JieqiMove | null;
  // 延迟分配模式：AI 翻棋需要用户选择类型
  pending_ai_reveal: JieqiMove | null;
  pending_ai_reveal_types: string[] | null;
}

// 创建游戏请求
export interface CreateJieqiGameOptions {
  mode: GameMode;
  ai_level?: AILevel;
  ai_color?: string;
  ai_strategy?: AIStrategy;
  seed?: number;
  // AI vs AI 模式下指定双方 AI 策略
  red_ai_strategy?: AIStrategy;
  black_ai_strategy?: AIStrategy;
  // 延迟分配模式：翻棋时决定身份
  delay_reveal?: boolean;
}

// 可用棋子类型响应（延迟分配模式）
export interface AvailableTypesResponse {
  position: Position;
  available_types: string[];  // 可选择的棋子类型列表（可能重复）
  unique_types: string[];     // 去重后的类型列表
}

// 带 reveal_type 的移动请求
export interface JieqiMoveRequest {
  action_type: ActionType;
  from_pos: Position;
  to_pos: Position;
  reveal_type?: PieceType;  // 延迟分配模式下指定翻出的类型
}

// AI 策略信息（从后端获取）
export interface AIStrategyInfo {
  name: string;
  description: string;
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

// 评估结果
export interface EvaluationResult {
  total: number;
  material: { red: number; black: number; diff: number };
  position: { red: number; black: number; diff: number };
  check: number;
  hidden: { red: number; black: number };
  piece_count: { red: number; black: number };
  win_probability: number;
  move_count: number;
  current_turn: Color;
}

// 走棋历史项
export interface MoveHistoryItem {
  move_number: number;
  move: JieqiMove;
  notation: string;
  captured?: JieqiPiece;
  revealed_type?: PieceType;
}

// 历史响应
export interface HistoryResponse {
  game_id: string;
  moves: MoveHistoryItem[];
  total_moves: number;
}

// 复盘响应
export interface ReplayResponse {
  success: boolean;
  game_state?: JieqiGameState;
  current_move_number: number;
  total_moves: number;
  error?: string;
}
