// 主应用组件

import { useState, useCallback } from 'react';
import { Board } from './components/Board';
import { GameControls } from './components/GameControls';
import { createGame, makeMove, requestAIMove } from './api';
import type { AILevel, GameMode, GameState, Move, Position } from './types';
import './App.css';

function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNewGame = useCallback(async (mode: GameMode, aiLevel: AILevel, aiColor: string) => {
    setIsLoading(true);
    setError(null);
    setSelectedPosition(null);

    try {
      const state = await createGame(mode, aiLevel, aiColor);
      setGameState(state);
    } catch (err) {
      setError('Failed to create game. Is the server running?');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleMove = useCallback(async (move: Move) => {
    if (!gameState) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await makeMove(gameState.game_id, move);
      if (response.success && response.game_state) {
        setGameState(response.game_state);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError('Failed to make move');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [gameState]);

  const handleRequestAIMove = useCallback(async () => {
    if (!gameState) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await requestAIMove(gameState.game_id);
      if (response.success && response.game_state) {
        setGameState(response.game_state);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError('Failed to get AI move');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [gameState]);

  return (
    <div className="app">
      <div className="game-area">
        {gameState ? (
          <Board
            gameState={gameState}
            selectedPosition={selectedPosition}
            onSelectPosition={setSelectedPosition}
            onMove={handleMove}
          />
        ) : (
          <div className="no-game">
            <p>Start a new game to begin playing</p>
          </div>
        )}
      </div>

      <div className="controls-area">
        <GameControls
          gameState={gameState}
          onNewGame={handleNewGame}
          onRequestAIMove={handleRequestAIMove}
          isLoading={isLoading}
        />

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
