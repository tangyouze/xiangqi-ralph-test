// 揭棋游戏控制组件

import { useState, useEffect, useRef, useCallback } from 'react';
import type { AIStrategyInfo, CreateJieqiGameOptions, GameMode, JieqiGameState, AITimeLimit, AIBackend, AIInfoResponse } from './types';
import { AI_TIME_OPTIONS } from './types';
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
  const [mode, setMode] = useState<GameMode>('human_vs_ai');  // 默认人机对战
  const [aiColor, setAIColor] = useState<string>('black');
  const [aiStrategy, setAIStrategy] = useState<string>('minimax');  // 默认策略
  const [aiBackend, setAIBackend] = useState<AIBackend>('rust');  // 默认 Rust
  const [redAIStrategy, setRedAIStrategy] = useState<string>('minimax');
  const [blackAIStrategy, setBlackAIStrategy] = useState<string>('minimax');
  const [redAIBackend, setRedAIBackend] = useState<AIBackend>('rust');
  const [blackAIBackend, setBlackAIBackend] = useState<AIBackend>('rust');
  const [delayReveal, setDelayReveal] = useState<boolean>(true);  // 默认开启延迟分配模式

  // AI 思考时间限制
  const [aiTimeLimit, setAITimeLimit] = useState<AITimeLimit>(15);  // 默认 15 秒
  const [redAITimeLimit, setRedAITimeLimit] = useState<AITimeLimit>(15);
  const [blackAITimeLimit, setBlackAITimeLimit] = useState<AITimeLimit>(15);

  // AI 策略列表（从后端获取）
  const [aiStrategies, setAiStrategies] = useState<AIStrategyInfo[]>([]);
  const [rustStrategies, setRustStrategies] = useState<string[]>([]);

  // 获取 AI 信息
  useEffect(() => {
    getAIInfo()
      .then((info: AIInfoResponse) => {
        setAiStrategies(info.available_strategies);
        setRustStrategies(info.rust_strategies || []);
        // 默认使用 Rust 支持的 minimax 策略
        const defaultStrategy = info.rust_strategies?.includes('minimax') ? 'minimax' : 'greedy';
        setAIStrategy(defaultStrategy);
        setRedAIStrategy(defaultStrategy);
        setBlackAIStrategy(defaultStrategy);
      })
      .catch(err => console.error('Failed to load AI strategies:', err));
  }, []);

  // 获取当前后端支持的策略
  const getStrategiesForBackend = (backend: AIBackend) => {
    if (backend === 'rust') {
      return aiStrategies.filter(s => rustStrategies.includes(s.name));
    }
    return aiStrategies;
  };

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
      delay_reveal: delayReveal,
      ai_backend: aiBackend,
    };

    if (mode === 'human_vs_ai') {
      options.ai_strategy = aiStrategy;
      options.ai_time_limit = aiTimeLimit;
    } else if (mode === 'ai_vs_ai') {
      options.red_ai_strategy = redAIStrategy;
      options.black_ai_strategy = blackAIStrategy;
      options.red_ai_backend = redAIBackend;
      options.black_ai_backend = blackAIBackend;
      options.red_ai_time_limit = redAITimeLimit;
      options.black_ai_time_limit = blackAITimeLimit;
    }

    onNewGame(options);
  }, [mode, aiColor, aiStrategy, aiBackend, redAIStrategy, blackAIStrategy, redAIBackend, blackAIBackend, delayReveal, aiTimeLimit, redAITimeLimit, blackAITimeLimit, onNewGame]);

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

        <div className="control-group checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={delayReveal}
              onChange={e => setDelayReveal(e.target.checked)}
            />
            Manual Reveal (choose piece type when revealing)
          </label>
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
              <label htmlFor="aiBackend">AI Backend:</label>
              <select id="aiBackend" value={aiBackend} onChange={e => {
                const newBackend = e.target.value as AIBackend;
                setAIBackend(newBackend);
                // 切换后端时，选择该后端支持的默认策略
                const strategies = getStrategiesForBackend(newBackend);
                if (strategies.length > 0 && !strategies.find(s => s.name === aiStrategy)) {
                  setAIStrategy(strategies[0].name);
                }
              }}>
                <option value="rust">Rust (Fast)</option>
                <option value="python">Python (More strategies)</option>
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="aiStrategy">AI Strategy:</label>
              <select id="aiStrategy" value={aiStrategy} onChange={e => setAIStrategy(e.target.value)}>
                {getStrategiesForBackend(aiBackend).map(s => (
                  <option key={s.name} value={s.name} title={s.description}>{s.name} - {s.description}</option>
                ))}
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="aiTime">AI Time (s):</label>
              <select id="aiTime" value={aiTimeLimit} onChange={e => setAITimeLimit(Number(e.target.value) as AITimeLimit)}>
                {AI_TIME_OPTIONS.map(t => (
                  <option key={t} value={t}>{t}s</option>
                ))}
              </select>
            </div>
          </>
        )}

        {mode === 'ai_vs_ai' && (
          <>
            <div className="control-group">
              <label htmlFor="redBackend">Red Backend:</label>
              <select id="redBackend" value={redAIBackend} onChange={e => {
                const newBackend = e.target.value as AIBackend;
                setRedAIBackend(newBackend);
                const strategies = getStrategiesForBackend(newBackend);
                if (strategies.length > 0 && !strategies.find(s => s.name === redAIStrategy)) {
                  setRedAIStrategy(strategies[0].name);
                }
              }}>
                <option value="rust">Rust</option>
                <option value="python">Python</option>
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="redAI">Red AI:</label>
              <select id="redAI" value={redAIStrategy} onChange={e => setRedAIStrategy(e.target.value)}>
                {getStrategiesForBackend(redAIBackend).map(s => (
                  <option key={s.name} value={s.name} title={s.description}>{s.name} - {s.description}</option>
                ))}
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="redAITime">Red Time (s):</label>
              <select id="redAITime" value={redAITimeLimit} onChange={e => setRedAITimeLimit(Number(e.target.value) as AITimeLimit)}>
                {AI_TIME_OPTIONS.map(t => (
                  <option key={t} value={t}>{t}s</option>
                ))}
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="blackBackend">Black Backend:</label>
              <select id="blackBackend" value={blackAIBackend} onChange={e => {
                const newBackend = e.target.value as AIBackend;
                setBlackAIBackend(newBackend);
                const strategies = getStrategiesForBackend(newBackend);
                if (strategies.length > 0 && !strategies.find(s => s.name === blackAIStrategy)) {
                  setBlackAIStrategy(strategies[0].name);
                }
              }}>
                <option value="rust">Rust</option>
                <option value="python">Python</option>
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="blackAI">Black AI:</label>
              <select id="blackAI" value={blackAIStrategy} onChange={e => setBlackAIStrategy(e.target.value)}>
                {getStrategiesForBackend(blackAIBackend).map(s => (
                  <option key={s.name} value={s.name} title={s.description}>{s.name} - {s.description}</option>
                ))}
              </select>
            </div>
            <div className="control-group">
              <label htmlFor="blackAITime">Black Time (s):</label>
              <select id="blackAITime" value={blackAITimeLimit} onChange={e => setBlackAITimeLimit(Number(e.target.value) as AITimeLimit)}>
                {AI_TIME_OPTIONS.map(t => (
                  <option key={t} value={t}>{t}s</option>
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

    </div>
  );
}
