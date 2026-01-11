// 揭棋游戏控制组件

import { useState, useEffect, useRef, useCallback } from 'react';
import type { AIStrategyInfo, CreateJieqiGameOptions, GameMode, JieqiGameState } from './types';
import { getAIInfo } from './api';
import './JieqiGameControls.css';

interface JieqiGameControlsProps {
  gameState: JieqiGameState | null;
  onNewGame: (options: CreateJieqiGameOptions) => void;
  onRequestAIMove: () => void;
  isLoading: boolean;
}

export function JieqiGameControls({
  gameState,
  onNewGame,
  onRequestAIMove,
  isLoading,
}: JieqiGameControlsProps) {
  const [mode, setMode] = useState<GameMode>('ai_vs_ai');
  const [aiColor, setAIColor] = useState<string>('black');
  const [aiStrategy, setAIStrategy] = useState<string>('greedy');
  const [redAIStrategy, setRedAIStrategy] = useState<string>('greedy');
  const [blackAIStrategy, setBlackAIStrategy] = useState<string>('random');

  // AI 策略列表（从后端获取）
  const [aiStrategies, setAiStrategies] = useState<AIStrategyInfo[]>([]);

  // 获取 AI 信息
  useEffect(() => {
    getAIInfo()
      .then(info => {
        setAiStrategies(info.available_strategies);
        // 设置默认策略
        if (info.available_strategies.length > 0) {
          const defaultStrategy = info.available_strategies.find(s => s.name === 'greedy')?.name
            || info.available_strategies[0].name;
          setAiStrategy(defaultStrategy);
          setRedAIStrategy(defaultStrategy);
          // 黑方用 random 作为默认（用于对比测试）
          const randomStrategy = info.available_strategies.find(s => s.name === 'random')?.name
            || info.available_strategies[0].name;
          setBlackAIStrategy(randomStrategy);
        }
      })
      .catch(err => console.error('Failed to load AI strategies:', err));
  }, []);

  // 自动播放
  const [autoPlay, setAutoPlay] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(1000);
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

    const options: CreateJieqiGameOptions = {
      mode,
      ai_color: aiColor,
    };

    if (mode === 'human_vs_ai') {
      options.ai_strategy = aiStrategy;
    } else if (mode === 'ai_vs_ai') {
      options.red_ai_strategy = redAIStrategy;
      options.black_ai_strategy = blackAIStrategy;
    }

    onNewGame(options);
  }, [mode, aiColor, aiStrategy, redAIStrategy, blackAIStrategy, onNewGame]);

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
    <div className="jieqi-game-controls">
      <h2>Jieqi (Reveal Chess)</h2>

      <div className="status-panel">
        <div className={`status ${gameState?.result !== 'ongoing' ? 'game-over' : ''}`}>
          {getStatusText()}
        </div>
        {gameState && (
          <>
            <div className="move-count">
              Moves: {gameState.move_count}
            </div>
            <div className="hidden-count">
              Hidden pieces - Red: {gameState.hidden_count.red}, Black: {gameState.hidden_count.black}
            </div>
          </>
        )}
      </div>

      <div className="new-game-panel">
        <h3>New Game</h3>

        <div className="control-group">
          <label htmlFor="mode">Mode:</label>
          <select id="mode" value={mode} onChange={e => setMode(e.target.value as GameMode)}>
            <option value="human_vs_human">Human vs Human</option>
            <option value="human_vs_ai">Human vs AI</option>
            <option value="ai_vs_ai">AI vs AI</option>
          </select>
        </div>

        {mode === 'human_vs_ai' && (
          <>
            <div className="control-group">
              <label htmlFor="aiColor">AI plays:</label>
              <select id="aiColor" value={aiColor} onChange={e => setAIColor(e.target.value)}>
                <option value="black">Black</option>
                <option value="red">Red</option>
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="aiStrategy">AI Strategy:</label>
              <select id="aiStrategy" value={aiStrategy} onChange={e => setAIStrategy(e.target.value)}>
                {aiStrategies.map(s => (
                  <option key={s.name} value={s.name} title={s.description}>{s.name} - {s.description}</option>
                ))}
              </select>
            </div>
          </>
        )}

        {mode === 'ai_vs_ai' && (
          <>
            <div className="control-group">
              <label htmlFor="redAI">Red AI:</label>
              <select id="redAI" value={redAIStrategy} onChange={e => setRedAIStrategy(e.target.value)}>
                {aiStrategies.map(s => (
                  <option key={s.name} value={s.name} title={s.description}>{s.name} - {s.description}</option>
                ))}
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="blackAI">Black AI:</label>
              <select id="blackAI" value={blackAIStrategy} onChange={e => setBlackAIStrategy(e.target.value)}>
                {aiStrategies.map(s => (
                  <option key={s.name} value={s.name} title={s.description}>{s.name} - {s.description}</option>
                ))}
              </select>
            </div>
          </>
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

      <div className="rules-panel">
        <h4>Jieqi Rules</h4>
        <ul>
          <li>Only Kings start revealed; all other pieces are hidden</li>
          <li>Hidden pieces move based on their position's piece type</li>
          <li>When a hidden piece moves, it gets revealed</li>
          <li>Revealed Elephants and Advisors can cross the river</li>
          <li>Capture the opponent's King to win</li>
        </ul>
      </div>
    </div>
  );
}
