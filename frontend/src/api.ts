// API 调用封装

import type { AILevel, GameMode, GameState, Move, MoveResponse } from './types';

const API_BASE = 'http://localhost:8000';

export async function createGame(
  mode: GameMode,
  aiLevel: AILevel = 'easy',
  aiColor: string = 'black'
): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mode,
      ai_level: aiLevel,
      ai_color: aiColor,
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to create game');
  }
  return response.json();
}

export async function getGame(gameId: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${gameId}`);
  if (!response.ok) {
    throw new Error('Failed to get game');
  }
  return response.json();
}

export async function makeMove(gameId: string, move: Move): Promise<MoveResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: move.from,
      to: move.to,
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to make move');
  }
  return response.json();
}

export async function requestAIMove(gameId: string): Promise<MoveResponse> {
  const response = await fetch(`${API_BASE}/games/${gameId}/ai-move`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to request AI move');
  }
  return response.json();
}

export async function deleteGame(gameId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/games/${gameId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete game');
  }
}
