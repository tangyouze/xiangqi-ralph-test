// 揭棋评估和复盘组件

import { useState, useEffect, useCallback } from 'react';
import type { EvaluationResult, HistoryResponse, JieqiGameState, MoveHistoryItem } from './types';
import { evaluatePosition, getHistory, replayToMove } from './api';
import './JieqiEvaluation.css';

interface JieqiEvaluationProps {
  gameState: JieqiGameState | null;
  onGameStateChange: (state: JieqiGameState) => void;
}

export function JieqiEvaluation({ gameState, onGameStateChange }: JieqiEvaluationProps) {
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [maxMoves, setMaxMoves] = useState(0); // 跟踪最大步数

  // 获取评估和历史
  useEffect(() => {
    if (!gameState) {
      setEvaluation(null);
      setHistory(null);
      setMaxMoves(0);
      return;
    }

    const fetchData = async () => {
      try {
        const [evalResult, histResult] = await Promise.all([
          evaluatePosition(gameState.game_id),
          getHistory(gameState.game_id),
        ]);
        setEvaluation(evalResult);
        setHistory(histResult);
        // 更新最大步数（只增加，不减少）
        setMaxMoves(prev => Math.max(prev, histResult.total_moves));
      } catch (err) {
        console.error('Failed to fetch evaluation/history:', err);
      }
    };

    fetchData();
  }, [gameState]);

  // 复盘到指定步数
  const handleReplay = useCallback(async (moveNumber: number) => {
    if (!gameState || isLoading) return;

    setIsLoading(true);
    try {
      const result = await replayToMove(gameState.game_id, moveNumber);
      if (result.success && result.game_state) {
        onGameStateChange(result.game_state);
      }
    } catch (err) {
      console.error('Failed to replay:', err);
    } finally {
      setIsLoading(false);
    }
  }, [gameState, isLoading, onGameStateChange]);

  if (!gameState) {
    return null;
  }

  const currentMove = history?.total_moves ?? 0;
  const winProb = evaluation?.win_probability ?? 0.5;
  const winProbPercent = Math.round(winProb * 100);

  // 格式化分数显示
  const formatScore = (score: number) => {
    if (score > 0) return `+${score}`;
    return score.toString();
  };

  return (
    <div className="jieqi-evaluation">
      <h3>Position Evaluation</h3>

      {evaluation && (
        <div className="eval-content">
          {/* 胜率条 */}
          <div className="win-bar-container">
            <div className="win-bar">
              <div
                className="win-bar-red"
                style={{ width: `${winProbPercent}%` }}
              />
              <div
                className="win-bar-black"
                style={{ width: `${100 - winProbPercent}%` }}
              />
            </div>
            <div className="win-labels">
              <span className="red-label">{winProbPercent}%</span>
              <span className="black-label">{100 - winProbPercent}%</span>
            </div>
          </div>

          {/* 分数详情 */}
          <div className="score-details">
            <div className="score-row">
              <span className="label">Total Score:</span>
              <span className={`value ${evaluation.total > 0 ? 'positive' : evaluation.total < 0 ? 'negative' : ''}`}>
                {formatScore(evaluation.total)}
              </span>
            </div>
            <div className="score-row">
              <span className="label">Material:</span>
              <span className="value">{formatScore(evaluation.material.diff)}</span>
              <span className="detail">(R:{evaluation.material.red} B:{evaluation.material.black})</span>
            </div>
            <div className="score-row">
              <span className="label">Position:</span>
              <span className="value">{formatScore(evaluation.position.diff)}</span>
            </div>
            {evaluation.check !== 0 && (
              <div className="score-row">
                <span className="label">Check:</span>
                <span className={`value ${evaluation.check > 0 ? 'positive' : 'negative'}`}>
                  {formatScore(evaluation.check)}
                </span>
              </div>
            )}
            <div className="score-row">
              <span className="label">Pieces:</span>
              <span className="detail">Red: {evaluation.piece_count.red}, Black: {evaluation.piece_count.black}</span>
            </div>
          </div>
        </div>
      )}

      {/* 复盘控制 */}
      <div className="replay-controls">
        <h4>Replay</h4>
        <div className="replay-buttons">
          <button
            onClick={() => handleReplay(0)}
            disabled={isLoading || currentMove === 0}
            title="Go to start"
          >
            ⏮
          </button>
          <button
            onClick={() => handleReplay(currentMove - 1)}
            disabled={isLoading || currentMove === 0}
            title="Previous move"
          >
            ◀
          </button>
          <span className="move-indicator">
            {currentMove} / {maxMoves}
          </span>
          <button
            onClick={() => handleReplay(currentMove + 1)}
            disabled={isLoading || currentMove >= maxMoves}
            title="Next move"
          >
            ▶
          </button>
          <button
            onClick={() => handleReplay(maxMoves)}
            disabled={isLoading || currentMove >= maxMoves}
            title="Go to latest"
          >
            ⏭
          </button>
        </div>
      </div>

      {/* 历史记录 */}
      <div className="history-section">
        <button
          className="toggle-history"
          onClick={() => setShowHistory(!showHistory)}
        >
          {showHistory ? '▼ Hide History' : '▶ Show History'}
        </button>

        {showHistory && history && (
          <div className="history-list">
            {history.moves.length === 0 ? (
              <div className="no-moves">No moves yet</div>
            ) : (
              history.moves.map((item: MoveHistoryItem) => (
                <div
                  key={item.move_number}
                  className={`history-item ${item.move_number === currentMove ? 'current' : ''}`}
                  onClick={() => handleReplay(item.move_number)}
                >
                  <span className="move-num">{item.move_number}.</span>
                  <span className="notation">{item.notation}</span>
                  {item.captured && <span className="captured">×</span>}
                  {item.revealed_type && <span className="revealed">({item.revealed_type})</span>}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
