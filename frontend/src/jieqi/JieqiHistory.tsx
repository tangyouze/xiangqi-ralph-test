// 揭棋走棋历史组件

import { useState, useEffect, useCallback } from 'react';
import { getHistory } from './api';
import type { JieqiGameState, MoveHistoryItem } from './types';
import './JieqiHistory.css';

interface JieqiHistoryProps {
  gameState: JieqiGameState | null;
}

export function JieqiHistory({ gameState }: JieqiHistoryProps) {
  const [history, setHistory] = useState<MoveHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (!gameState?.game_id) {
      setHistory([]);
      return;
    }

    setLoading(true);
    try {
      const response = await getHistory(gameState.game_id);
      setHistory(response.moves);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setLoading(false);
    }
  }, [gameState?.game_id]);

  // 当 move_count 变化时重新获取历史
  useEffect(() => {
    fetchHistory();
  }, [gameState?.move_count, fetchHistory]);

  if (!gameState) {
    return (
      <div className="jieqi-history">
        <h3>Move History</h3>
        <div className="history-empty">No game in progress</div>
      </div>
    );
  }

  // 将历史记录按回合分组（每两步一回合）
  const rounds: { round: number; red?: MoveHistoryItem; black?: MoveHistoryItem }[] = [];
  for (let i = 0; i < history.length; i++) {
    const move = history[i];
    const roundNum = Math.floor(i / 2) + 1;
    if (i % 2 === 0) {
      rounds.push({ round: roundNum, red: move });
    } else {
      if (rounds.length > 0) {
        rounds[rounds.length - 1].black = move;
      }
    }
  }

  return (
    <div className="jieqi-history">
      <h3>Move History ({history.length} moves)</h3>
      {loading ? (
        <div className="history-loading">Loading...</div>
      ) : history.length === 0 ? (
        <div className="history-empty">No moves yet</div>
      ) : (
        <div className="history-table-container">
          <table className="history-table">
            <thead>
              <tr>
                <th className="round-col">#</th>
                <th className="move-col red">Red</th>
                <th className="move-col black">Black</th>
              </tr>
            </thead>
            <tbody>
              {rounds.map((r) => (
                <tr key={r.round}>
                  <td className="round-col">{r.round}</td>
                  <td className="move-col red">
                    {r.red && (
                      <span className="notation" title={`Move ${r.red.move_number}`}>
                        {r.red.notation}
                      </span>
                    )}
                  </td>
                  <td className="move-col black">
                    {r.black && (
                      <span className="notation" title={`Move ${r.black.move_number}`}>
                        {r.black.notation}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
