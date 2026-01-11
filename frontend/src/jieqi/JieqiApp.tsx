// 揭棋主应用组件

import { useState, useCallback } from 'react';
import { JieqiBoard } from './JieqiBoard';
import { JieqiGameControls } from './JieqiGameControls';
import { JieqiEvaluation } from './JieqiEvaluation';
import { createJieqiGame, makeJieqiMove, requestJieqiAIMove, getAvailableTypes, executeAIMove } from './api';
import type { CreateJieqiGameOptions, JieqiGameState, JieqiMove, JieqiMoveRequest, PieceType, Position } from './types';
import { PIECE_NAMES } from './types';
import './JieqiApp.css';

// 揭棋类型选择模态框状态
interface RevealModalState {
  isOpen: boolean;
  pendingMove: JieqiMove | null;
  availableTypes: string[];
  uniqueTypes: string[];
  pieceColor: 'red' | 'black' | null;
  isAIMove: boolean;  // 是否为 AI 走棋（需要调用不同的 API）
}

export function JieqiApp() {
  const [gameState, setGameState] = useState<JieqiGameState | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 揭棋类型选择模态框
  const [revealModal, setRevealModal] = useState<RevealModalState>({
    isOpen: false,
    pendingMove: null,
    availableTypes: [],
    uniqueTypes: [],
    pieceColor: null,
    isAIMove: false,
  });

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

  // 实际执行走棋（带可选的 reveal_type）
  const executeMove = useCallback(async (move: JieqiMoveRequest) => {
    if (!gameState) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await makeJieqiMove(gameState.game_id, move);
      if (response.success && response.game_state) {
        setGameState(response.game_state);
        // 检查是否有 AI 翻棋需要用户选择类型
        if (response.pending_ai_reveal && response.pending_ai_reveal_types) {
          // 找出 AI 翻的棋子颜色
          const aiPiece = response.game_state.pieces.find(
            p => p.position.row === response.pending_ai_reveal!.from_pos.row
              && p.position.col === response.pending_ai_reveal!.from_pos.col
          );
          setRevealModal({
            isOpen: true,
            pendingMove: response.pending_ai_reveal,
            availableTypes: response.pending_ai_reveal_types,
            uniqueTypes: [...new Set(response.pending_ai_reveal_types)],
            pieceColor: aiPiece?.color || null,
            isAIMove: true,
          });
        }
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

  const handleMove = useCallback(async (move: JieqiMove) => {
    if (!gameState) return;

    // 如果是延迟分配模式且是翻棋走法，显示选择模态框
    if (gameState.delay_reveal && move.action_type === 'reveal_and_move') {
      setIsLoading(true);
      try {
        // 获取可用的棋子类型
        const typesResponse = await getAvailableTypes(gameState.game_id, move.from_pos);
        // 找出该棋子的颜色
        const piece = gameState.pieces.find(
          p => p.position.row === move.from_pos.row && p.position.col === move.from_pos.col
        );
        setRevealModal({
          isOpen: true,
          pendingMove: move,
          availableTypes: typesResponse.available_types,
          uniqueTypes: typesResponse.unique_types,
          pieceColor: piece?.color || null,
          isAIMove: false,
        });
      } catch (err) {
        setError('Failed to get available piece types');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // 普通走法直接执行
    executeMove(move);
  }, [gameState, executeMove]);

  // 执行 AI 翻棋走法（延迟分配模式）
  const executeAIMoveWithReveal = useCallback(async (move: JieqiMoveRequest) => {
    if (!gameState) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await executeAIMove(gameState.game_id, move);
      if (response.success && response.game_state) {
        setGameState(response.game_state);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err) {
      setError('Failed to execute AI move');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [gameState]);

  // 处理选择随机揭棋
  const handleRevealRandom = useCallback(() => {
    if (!revealModal.pendingMove) return;
    // 不传 reveal_type，后端会随机选择
    if (revealModal.isAIMove) {
      executeAIMoveWithReveal(revealModal.pendingMove);
    } else {
      executeMove(revealModal.pendingMove);
    }
    setRevealModal({ isOpen: false, pendingMove: null, availableTypes: [], uniqueTypes: [], pieceColor: null, isAIMove: false });
    setSelectedPosition(null);
  }, [revealModal.pendingMove, revealModal.isAIMove, executeMove, executeAIMoveWithReveal]);

  // 处理选择指定类型揭棋
  const handleRevealType = useCallback((pieceType: PieceType) => {
    if (!revealModal.pendingMove) return;
    const moveWithType = { ...revealModal.pendingMove, reveal_type: pieceType };
    if (revealModal.isAIMove) {
      executeAIMoveWithReveal(moveWithType);
    } else {
      executeMove(moveWithType);
    }
    setRevealModal({ isOpen: false, pendingMove: null, availableTypes: [], uniqueTypes: [], pieceColor: null, isAIMove: false });
    setSelectedPosition(null);
  }, [revealModal.pendingMove, revealModal.isAIMove, executeMove, executeAIMoveWithReveal]);

  // 取消揭棋选择
  const handleRevealCancel = useCallback(() => {
    setRevealModal({ isOpen: false, pendingMove: null, availableTypes: [], uniqueTypes: [], pieceColor: null, isAIMove: false });
  }, []);

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

  // 渲染揭棋类型选择模态框
  const renderRevealModal = () => {
    if (!revealModal.isOpen) return null;

    const color = revealModal.pieceColor || 'red';
    const title = revealModal.isAIMove ? 'AI Reveal - Choose Type' : 'Choose Piece Type';
    const description = revealModal.isAIMove
      ? 'AI wants to reveal a piece. Select which type to reveal, or let the system choose randomly.'
      : 'Select which piece to reveal, or let the system choose randomly.';

    return (
      <div className="reveal-modal-overlay" onClick={handleRevealCancel}>
        <div className="reveal-modal" onClick={e => e.stopPropagation()}>
          <h3>{title}</h3>
          <p>{description}</p>

          <div className="reveal-options">
            <button className="reveal-option random" onClick={handleRevealRandom}>
              🎲 Random
            </button>

            {revealModal.uniqueTypes.map((typeStr) => {
              const pieceType = typeStr as PieceType;
              const displayName = PIECE_NAMES[pieceType]?.[color] || typeStr;
              const count = revealModal.availableTypes.filter(t => t === typeStr).length;
              return (
                <button
                  key={typeStr}
                  className={`reveal-option piece-type ${color}`}
                  onClick={() => handleRevealType(pieceType)}
                >
                  <span className="piece-char">{displayName}</span>
                  <span className="piece-count">×{count}</span>
                </button>
              );
            })}
          </div>

          <button className="reveal-cancel" onClick={handleRevealCancel}>
            Cancel
          </button>
        </div>
      </div>
    );
  };

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

      {/* 揭棋类型选择模态框 */}
      {renderRevealModal()}
    </div>
  );
}

export default JieqiApp;
