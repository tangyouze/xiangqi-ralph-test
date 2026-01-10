// 游戏控制组件

import { useState, useEffect, useRef, useCallback } from 'react';
import type { AILevel, AIStrategyType, CreateGameOptions, GameMode, GameState } from '../types';
import { AI_STRATEGY_DESCRIPTIONS } from '../types';
import './GameControls.css';

interface GameControlsProps {
  gameState: GameState | null;
  onNewGame: (options: CreateGameOptions) => void;
  onRequestAIMove: () => void;
  isLoading: boolean;
}

export function GameControls({ gameState, onNewGame, onRequestAIMove, isLoading }: GameControlsProps) {
  const [mode, setMode] = useState<GameMode>('human_vs_ai');
  const [aiLevel, setAILevel] = useState<AILevel>('medium');
  const [aiColor, setAIColor] = useState<string>('black');

  // 高级设置
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [aiStrategy, setAIStrategy] = useState<AIStrategyType | ''>('');
  const [searchDepth, setSearchDepth] = useState<number>(3);

  // AI vs AI 设置
  const [redAIStrategy, setRedAIStrategy] = useState<AIStrategyType>('minimax');
  const [redSearchDepth, setRedSearchDepth] = useState<number>(3);
  const [blackAIStrategy, setBlackAIStrategy] = useState<AIStrategyType>('defensive');
  const [blackSearchDepth, setBlackSearchDepth] = useState<number>(3);

  // 自动播放
  const [autoPlay, setAutoPlay] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(1000); // ms between moves
  const autoPlayRef = useRef<number | null>(null);

  // 自动播放逻辑
  useEffect(() => {
    if (autoPlay && gameState && gameState.result === 'ongoing' && mode === 'ai_vs_ai' && !isLoading) {
      autoPlayRef.current = window.setTimeout(() => {
        onRequestAIMove();
      }, playSpeed);
    }

    return () => {
      if (autoPlayRef.current) {
        clearTimeout(autoPlayRef.current);
      }
    };
  }, [autoPlay, gameState, mode, isLoading, playSpeed, onRequestAIMove]);

  // 游戏结束时停止自动播放
  useEffect(() => {
    if (gameState?.result !== 'ongoing') {
      setAutoPlay(false);
    }
  }, [gameState?.result]);

  const handleNewGame = useCallback(() => {
    setAutoPlay(false);

    const options: CreateGameOptions = {
      mode,
      ai_level: aiLevel,
      ai_color: aiColor,
    };

    if (mode === 'human_vs_ai' && showAdvanced && aiStrategy) {
      options.ai_strategy = aiStrategy;
      if (aiStrategy === 'minimax') {
        options.search_depth = searchDepth;
      }
    }

    if (mode === 'ai_vs_ai') {
      options.red_ai_strategy = redAIStrategy;
      if (redAIStrategy === 'minimax') {
        options.red_search_depth = redSearchDepth;
      }
      options.black_ai_strategy = blackAIStrategy;
      if (blackAIStrategy === 'minimax') {
        options.black_search_depth = blackSearchDepth;
      }
    }

    onNewGame(options);
  }, [mode, aiLevel, aiColor, showAdvanced, aiStrategy, searchDepth, redAIStrategy, redSearchDepth, blackAIStrategy, blackSearchDepth, onNewGame]);

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

  const renderStrategySelect = (
    value: AIStrategyType | '',
    onChange: (v: AIStrategyType) => void,
    id: string
  ) => (
    <select id={id} value={value} onChange={e => onChange(e.target.value as AIStrategyType)}>
      <option value="random">Random</option>
      <option value="greedy">Greedy</option>
      <option value="defensive">Defensive</option>
      <option value="aggressive">Aggressive</option>
      <option value="minimax">Minimax (Deep Search)</option>
    </select>
  );

  const renderDepthInput = (value: number, onChange: (v: number) => void, id: string) => (
    <div className="control-group">
      <label htmlFor={id}>Search Depth (1-8):</label>
      <input
        id={id}
        type="number"
        min={1}
        max={8}
        value={value}
        onChange={e => onChange(Math.min(8, Math.max(1, parseInt(e.target.value) || 1)))}
      />
    </div>
  );

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
          <label htmlFor="mode">Mode:</label>
          <select id="mode" value={mode} onChange={e => setMode(e.target.value as GameMode)}>
            <option value="human_vs_human">Human vs Human</option>
            <option value="human_vs_ai">Human vs AI</option>
            <option value="ai_vs_ai">AI vs AI (Battle)</option>
          </select>
        </div>

        {mode === 'human_vs_ai' && (
          <>
            <div className="control-group">
              <label htmlFor="aiLevel">AI Level:</label>
              <select id="aiLevel" value={aiLevel} onChange={e => setAILevel(e.target.value as AILevel)}>
                <option value="random">Random (Weakest)</option>
                <option value="easy">Easy (Greedy)</option>
                <option value="medium">Medium (Defensive)</option>
                <option value="hard">Hard (Minimax D3)</option>
                <option value="expert">Expert (Minimax D4)</option>
              </select>
            </div>

            <div className="control-group">
              <label htmlFor="aiColor">AI plays:</label>
              <select id="aiColor" value={aiColor} onChange={e => setAIColor(e.target.value)}>
                <option value="black">Black</option>
                <option value="red">Red</option>
              </select>
            </div>

            <label className="advanced-toggle">
              <input
                type="checkbox"
                checked={showAdvanced}
                onChange={e => setShowAdvanced(e.target.checked)}
              />
              Advanced AI Settings
            </label>

            {showAdvanced && (
              <div className="advanced-settings">
                <div className="control-group">
                  <label htmlFor="aiStrategy">AI Strategy:</label>
                  {renderStrategySelect(aiStrategy || 'minimax', (v) => setAIStrategy(v), 'aiStrategy')}
                  <small style={{ color: '#888', display: 'block', marginTop: 4 }}>
                    {aiStrategy && AI_STRATEGY_DESCRIPTIONS[aiStrategy]}
                  </small>
                </div>

                {aiStrategy === 'minimax' && renderDepthInput(searchDepth, setSearchDepth, 'searchDepth')}
              </div>
            )}
          </>
        )}

        {mode === 'ai_vs_ai' && (
          <div className="ai-battle-panel">
            <h4>AI Battle Configuration</h4>

            <div className="ai-side-config red">
              <h5>Red AI</h5>
              <div className="control-group">
                <label htmlFor="redStrategy">Strategy:</label>
                {renderStrategySelect(redAIStrategy, setRedAIStrategy, 'redStrategy')}
              </div>
              {redAIStrategy === 'minimax' && renderDepthInput(redSearchDepth, setRedSearchDepth, 'redDepth')}
            </div>

            <div className="ai-side-config black">
              <h5>Black AI</h5>
              <div className="control-group">
                <label htmlFor="blackStrategy">Strategy:</label>
                {renderStrategySelect(blackAIStrategy, setBlackAIStrategy, 'blackStrategy')}
              </div>
              {blackAIStrategy === 'minimax' && renderDepthInput(blackSearchDepth, setBlackSearchDepth, 'blackDepth')}
            </div>
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
        <>
          <button
            className="ai-move-btn"
            onClick={onRequestAIMove}
            disabled={isLoading || autoPlay}
          >
            {isLoading ? 'Thinking...' : 'Next AI Move'}
          </button>

          <button
            className={`auto-play-btn ${autoPlay ? 'active' : ''}`}
            onClick={() => setAutoPlay(!autoPlay)}
            disabled={isLoading && !autoPlay}
          >
            {autoPlay ? 'Stop Auto Play' : 'Start Auto Play'}
          </button>

          {autoPlay && (
            <div className="speed-control">
              <label>Speed:</label>
              <input
                type="range"
                min={200}
                max={3000}
                step={100}
                value={playSpeed}
                onChange={e => setPlaySpeed(parseInt(e.target.value))}
              />
              <span>{(playSpeed / 1000).toFixed(1)}s</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
