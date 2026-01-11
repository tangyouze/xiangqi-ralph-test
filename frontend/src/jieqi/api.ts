// 揭棋 API 调用封装

import type { AIStrategyInfo, CreateJieqiGameOptions, JieqiGameState, JieqiMove, JieqiMoveResponse } from './types';

const API_BASE = 'http://localhost:6703';

// AI 信息响应
interface AIInfoResponse {
  available_strategies: AIStrategyInfo[];
  levels: string[];
  strategy_descriptions: Record<string, string>;
}

export async function getAIInfo(): Promise<AIInfoResponse> {
  const response = await fetch(`${API_BASE}/ai/info`);
  if (!response.ok) {
    throw new Error('Failed to get AI info');
  }
  return response.json();
}

export async function createJieqiGame(options: CreateJieqiGameOptions): Promise<JieqiGameState> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
  if (!response.ok) {
    throw new Error('Failed to create game');
  }
  return response.json();
}

export async function getJieqiGame(gameId: string): Promise<JieqiGameState> {
  const response = await fetch(`${API_BASE}/games/${gameId}`);
  if (!response.ok) {
    throw new Error('Failed to get game');
  }
  return response.json();
}

export async function makeJieqiMove(
  gameId: string,
  move: JieqiMove
): Promise<JieqiMoveResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action_type: move.action_type,
      from_row: move.from_pos.row,
      from_col: move.from_pos.col,
      to_row: move.to_pos.row,
      to_col: move.to_pos.col,
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to make move');
  }
  return response.json();
}

export async function requestJieqiAIMove(gameId: string): Promise<JieqiMoveResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/ai-move`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to request AI move');
  }
  return response.json();
}

export async function deleteJieqiGame(gameId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/games/${gameId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete game');
  }
}
