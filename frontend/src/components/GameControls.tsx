// 游戏控制组件

import { useState } from 'react';
import type { AILevel, GameMode, GameState } from '../types';
import './GameControls.css';

interface GameControlsProps {
  gameState: GameState | null;
  onNewGame: (mode: GameMode, aiLevel: AILevel, aiColor: string) => void;
  onRequestAIMove: () => void;
  isLoading: boolean;
}

export function GameControls({ gameState, onNewGame, onRequestAIMove, isLoading }: GameControlsProps) {
  const [mode, setMode] = useState<GameMode>('human_vs_ai');
  const [aiLevel, setAILevel] = useState<AILevel>('easy');
  const [aiColor, setAIColor] = useState<string>('black');

  const handleNewGame = () => {
    onNewGame(mode, aiLevel, aiColor);
  };

  const getStatusText = () => {
    if (!gameState) return 'No game in progress';

    if (gameState.result !== 'ongoing') {
      switch (gameState.result) {
        case 'red_win':
          return 'Red wins!';
        case 'black_win':
          return 'Black wins!';
        case 'draw':
          return 'Draw!';
      }
    }

    let status = gameState.current_turn === 'red' ? "Red's turn" : "Black's turn";
    if (gameState.is_in_check) {
      status += ' (Check!)';
    }
    return status;
  };

  return (
    <div className="game-controls">
      <h2>Chinese Chess</h2>

      <div className="status-panel">
        <div className={`status ${gameState?.result !== 'ongoing' ? 'game-over' : ''}`}>
          {getStatusText()}
        </div>
        {gameState && (
          <div className="move-count">
            Moves: {gameState.move_count}
          </div>
        )}
      </div>

      <div className="new-game-panel">
        <h3>New Game</h3>

        <div className="control-group">
          <label>Mode:</label>
          <select value={mode} onChange={e => setMode(e.target.value as GameMode)}>
            <option value="human_vs_human">Human vs Human</option>
            <option value="human_vs_ai">Human vs AI</option>
            <option value="ai_vs_ai">AI vs AI</option>
          </select>
        </div>

        {(mode === 'human_vs_ai' || mode === 'ai_vs_ai') && (
          <div className="control-group">
            <label>AI Level:</label>
            <select value={aiLevel} onChange={e => setAILevel(e.target.value as AILevel)}>
              <option value="random">Random</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        )}

        {mode === 'human_vs_ai' && (
          <div className="control-group">
            <label>AI plays:</label>
            <select value={aiColor} onChange={e => setAIColor(e.target.value)}>
              <option value="black">Black</option>
              <option value="red">Red</option>
            </select>
          </div>
        )}

        <button
          className="new-game-btn"
          onClick={handleNewGame}
          disabled={isLoading}
        >
          {isLoading ? 'Starting...' : 'Start New Game'}
        </button>
      </div>

      {gameState && mode === 'ai_vs_ai' && gameState.result === 'ongoing' && (
        <button
          className="ai-move-btn"
          onClick={onRequestAIMove}
          disabled={isLoading}
        >
          {isLoading ? 'Thinking...' : 'Next AI Move'}
        </button>
      )}
    </div>
  );
}
