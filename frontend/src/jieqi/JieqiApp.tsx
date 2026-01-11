// 揭棋主应用组件

import { useState, useCallback } from 'react';
import { JieqiBoard } from './JieqiBoard';
import { JieqiGameControls } from './JieqiGameControls';
import { JieqiEvaluation } from './JieqiEvaluation';
import { createJieqiGame, makeJieqiMove, requestJieqiAIMove } from './api';
import type { CreateJieqiGameOptions, JieqiGameState, JieqiMove, Position } from './types';
import './JieqiApp.css';

export function JieqiApp() {
  const [gameState, setGameState] = useState<JieqiGameState | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNewGame = useCallback(async (options: CreateJieqiGameOptions) => {
    setIsLoading(true);
    setError(null);
    setSelectedPosition(null);

    try {
      const state = await createJieqiGame(options);
      setGameState(state);
    } catch (err) {
      setError('Failed to create game. Is the Jieqi server running on port 6703?');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleMove = useCallback(async (move: JieqiMove) => {
    if (!gameState) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await makeJieqiMove(gameState.game_id, move);
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
      const response = await requestJieqiAIMove(gameState.game_id);
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
    <div className="jieqi-app">
      <div className="game-area">
        {gameState ? (
          <JieqiBoard
            gameState={gameState}
            selectedPosition={selectedPosition}
            onSelectPosition={setSelectedPosition}
            onMove={handleMove}
          />
        ) : (
          <div className="no-game">
            <p>Start a new Jieqi game to begin playing</p>
          </div>
        )}
      </div>

      <div className="controls-area">
        <JieqiGameControls
          gameState={gameState}
          onNewGame={handleNewGame}
          onRequestAIMove={handleRequestAIMove}
          isLoading={isLoading}
        />

        <JieqiEvaluation
          gameState={gameState}
          onGameStateChange={setGameState}
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

export default JieqiApp;
