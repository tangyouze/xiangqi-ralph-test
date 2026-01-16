//! Muses AI 策略 - 参考 miaosisrai 揭棋 AI
//!
//! 核心特性：
//! 1. Principal Variation Search (PVS) - 主变搜索
//! 2. Transposition Table (TT) - 置换表
//! 3. Late Move Reduction (LMR) - 后期走法剪枝
//! 4. Quiescence Search - 静态搜索
//! 5. MVV-LVA 走法排序
//! 6. Killer moves & History heuristic
//! 7. 时间控制的迭代加深

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{ActionType, Color, JieqiMove, PieceType, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
use std::sync::atomic::Ordering as AtomicOrdering;
use std::time::{Duration, Instant};

use super::NODE_COUNT;

// ============================================================================
// Zobrist Hashing
// ============================================================================

/// Zobrist 哈希表
struct ZobristTable {
    pieces: [[[u64; 2]; 16]; 90],
    turn: u64,
}

impl ZobristTable {
    #[allow(clippy::needless_range_loop)]
    fn new() -> Self {
        let mut rng = StdRng::seed_from_u64(0xDEADCAFE);
        let mut pieces = [[[0u64; 2]; 16]; 90];

        for pos in 0..90 {
            for idx in 0..16 {
                for hidden in 0..2 {
                    pieces[pos][idx][hidden] = rng.gen();
                }
            }
        }

        ZobristTable {
            pieces,
            turn: rng.gen(),
        }
    }

    #[inline]
    fn piece_hash(
        &self,
        pos: usize,
        color: Color,
        piece_type: Option<PieceType>,
        is_hidden: bool,
    ) -> u64 {
        let pt_idx = match piece_type {
            None => 0,
            Some(PieceType::King) => 1,
            Some(PieceType::Advisor) => 2,
            Some(PieceType::Elephant) => 3,
            Some(PieceType::Horse) => 4,
            Some(PieceType::Rook) => 5,
            Some(PieceType::Cannon) => 6,
            Some(PieceType::Pawn) => 7,
        };
        let color_idx = if color == Color::Red { 0 } else { 8 };
        self.pieces[pos][color_idx + pt_idx][is_hidden as usize]
    }
}

lazy_static::lazy_static! {
    static ref ZOBRIST: ZobristTable = ZobristTable::new();
}

/// 计算棋盘 Zobrist 哈希
#[inline]
fn compute_hash(board: &Board) -> u64 {
    let mut hash = 0u64;

    for piece in board.get_all_pieces(None) {
        let pos_idx = piece.position.to_index();
        hash ^= ZOBRIST.piece_hash(pos_idx, piece.color, piece.actual_type, piece.is_hidden);
    }

    if board.current_turn() == Color::Black {
        hash ^= ZOBRIST.turn;
    }

    hash
}

// ============================================================================
// Transposition Table
// ============================================================================

const TT_SIZE: usize = 1 << 20; // 1M entries
const TT_MASK: usize = TT_SIZE - 1;

#[derive(Clone, Copy, PartialEq)]
#[repr(u8)]
enum TTFlag {
    None = 0,
    Exact = 1,
    LowerBound = 2,
    UpperBound = 3,
}

#[derive(Clone, Copy)]
struct TTEntry {
    hash: u64,
    score: i32,
    depth: i8,
    flag: TTFlag,
    best_move: Option<JieqiMove>,
}

impl Default for TTEntry {
    fn default() -> Self {
        TTEntry {
            hash: 0,
            score: 0,
            depth: -1,
            flag: TTFlag::None,
            best_move: None,
        }
    }
}

struct TranspositionTable {
    entries: Vec<TTEntry>,
    hits: u64,
    misses: u64,
}

impl TranspositionTable {
    fn new() -> Self {
        TranspositionTable {
            entries: vec![TTEntry::default(); TT_SIZE],
            hits: 0,
            misses: 0,
        }
    }

    #[inline]
    fn get(&mut self, hash: u64) -> Option<&TTEntry> {
        let idx = (hash as usize) & TT_MASK;
        let entry = &self.entries[idx];
        if entry.hash == hash && entry.flag != TTFlag::None {
            self.hits += 1;
            Some(entry)
        } else {
            self.misses += 1;
            None
        }
    }

    #[inline]
    fn store(
        &mut self,
        hash: u64,
        depth: i8,
        score: i32,
        flag: TTFlag,
        best_move: Option<JieqiMove>,
    ) {
        let idx = (hash as usize) & TT_MASK;
        let entry = &mut self.entries[idx];

        // 深度替换策略
        if entry.hash != hash || depth >= entry.depth {
            entry.hash = hash;
            entry.depth = depth;
            entry.score = score;
            entry.flag = flag;
            entry.best_move = best_move;
        }
    }
}

// ============================================================================
// 搜索参数
// ============================================================================

const MATE_SCORE: i32 = 10000;
const QS_DEPTH_LIMIT: i32 = 4; // 静态搜索最大深度
const LMR_FULL_DEPTH_MOVES: usize = 4;
const LMR_REDUCTION_LIMIT: i32 = 3;
const DEFAULT_DEPTH: u32 = 5;
const MAX_DEPTH: u32 = 30;

// ============================================================================
// Muses AI
// ============================================================================

/// Muses AI - 参考 miaosisrai 揭棋 AI
pub struct MusesAI {
    max_depth: u32,
    rng: StdRng,
    randomness: f64,
    time_limit: Option<Duration>,
    // 搜索状态
    tt: TranspositionTable,
    history: Vec<Vec<i32>>,               // [from][to]
    killers: Vec<[Option<JieqiMove>; 2]>, // [ply][slot]
    start_time: Instant,
    best_move_at_depth: Vec<Option<(JieqiMove, i32)>>,
    nodes_evaluated: u64,
}

impl MusesAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };

        // 如果设置了时间限制，使用最大深度；否则使用配置深度
        let max_depth = if config.time_limit.is_some() {
            MAX_DEPTH
        } else if config.depth > 0 {
            config.depth.max(DEFAULT_DEPTH)
        } else {
            DEFAULT_DEPTH
        };

        MusesAI {
            max_depth,
            rng,
            randomness: config.randomness,
            time_limit: config.time_limit.map(Duration::from_secs_f64),
            tt: TranspositionTable::new(),
            history: vec![vec![0; 90]; 90],
            killers: vec![[None; 2]; 64],
            start_time: Instant::now(),
            best_move_at_depth: vec![None; 64],
            nodes_evaluated: 0,
        }
    }

    #[inline]
    fn is_time_up(&self) -> bool {
        if let Some(limit) = self.time_limit {
            self.start_time.elapsed() >= limit
        } else {
            false
        }
    }

    /// 评估局面
    #[inline]
    fn evaluate(&self, board: &Board, color: Color) -> i32 {
        let mut score: i32 = 0;

        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                HIDDEN_PIECE_VALUE
            } else {
                piece.actual_type.map_or(0, |pt| pt.value())
            };

            if piece.color == color {
                score += value;
                // 中心控制奖励
                let center_bonus = 5 - (4 - piece.position.col as i32).abs();
                score += center_bonus;

                // 前进奖励（兵）
                if piece.get_movement_type() == PieceType::Pawn {
                    let progress = if color == Color::Red {
                        piece.position.row as i32
                    } else {
                        9 - piece.position.row as i32
                    };
                    score += progress * 5;
                }
            } else {
                score -= value;
            }
        }

        score
    }

    /// 获取棋子价值
    #[inline]
    fn get_piece_value(piece: &crate::board::Piece) -> i32 {
        if piece.is_hidden {
            HIDDEN_PIECE_VALUE
        } else {
            piece.actual_type.map_or(0, |pt| pt.value())
        }
    }

    /// MVV-LVA 评分
    #[inline]
    fn mvv_lva_score(&self, board: &Board, mv: &JieqiMove) -> i32 {
        let victim = board.get_piece(mv.to_pos).map_or(0, Self::get_piece_value);
        let attacker = board
            .get_piece(mv.from_pos)
            .map_or(0, Self::get_piece_value);
        victim * 10 - attacker
    }

    /// 走法排序
    fn order_moves(
        &self,
        board: &Board,
        moves: &[JieqiMove],
        color: Color,
        ply: usize,
        tt_move: Option<JieqiMove>,
        prev_best: Option<JieqiMove>,
    ) -> Vec<JieqiMove> {
        let mut scored: Vec<(i32, JieqiMove)> = moves
            .iter()
            .map(|mv| {
                let mut score: i32 = 0;

                // 上一次迭代最佳走法
                if prev_best == Some(*mv) {
                    score += 20_000_000;
                }

                // TT 最佳走法
                if tt_move == Some(*mv) {
                    score += 10_000_000;
                }

                // 吃子 MVV-LVA
                if let Some(target) = board.get_piece(mv.to_pos) {
                    if target.color != color {
                        score += 1_000_000 + self.mvv_lva_score(board, mv);
                    }
                }

                // Killer moves
                if ply < 64
                    && (self.killers[ply][0] == Some(*mv) || self.killers[ply][1] == Some(*mv))
                {
                    score += 500_000;
                }

                // History heuristic
                score += self.history[mv.from_pos.to_index()][mv.to_pos.to_index()];

                // 揭子走法
                if mv.action_type == ActionType::RevealAndMove {
                    // 过河揭子更有价值
                    let is_over_river = if color == Color::Red {
                        mv.to_pos.row >= 5
                    } else {
                        mv.to_pos.row <= 4
                    };
                    if is_over_river {
                        score += 300;
                    } else {
                        score += 100;
                    }
                }

                (score, *mv)
            })
            .collect();

        scored.sort_by(|a, b| b.0.cmp(&a.0));
        scored.into_iter().map(|(_, mv)| mv).collect()
    }

    #[inline]
    fn update_killers(&mut self, mv: JieqiMove, ply: usize) {
        if ply >= 64 {
            return;
        }
        if self.killers[ply][0] != Some(mv) {
            self.killers[ply][1] = self.killers[ply][0];
            self.killers[ply][0] = Some(mv);
        }
    }

    #[inline]
    fn update_history(&mut self, mv: &JieqiMove, depth: i32) {
        let from_idx = mv.from_pos.to_index();
        let to_idx = mv.to_pos.to_index();
        self.history[from_idx][to_idx] += depth * depth;

        // 衰减
        if self.history[from_idx][to_idx] > 1_000_000 {
            for row in &mut self.history {
                for v in row.iter_mut() {
                    *v /= 2;
                }
            }
        }
    }

    /// 获取吃子走法
    fn get_captures(&self, board: &Board, color: Color) -> Vec<JieqiMove> {
        let legal_moves = board.get_legal_moves(color);
        legal_moves
            .into_iter()
            .filter(|mv| {
                board
                    .get_piece(mv.to_pos)
                    .is_some_and(|target| target.color != color)
            })
            .collect()
    }

    /// 静态搜索 - 避免水平线效应
    fn quiescence(
        &mut self,
        board: &mut Board,
        mut alpha: i32,
        beta: i32,
        color: Color,
        ply: i32,
        qs_depth: i32,
    ) -> i32 {
        let stand_pat = self.evaluate(board, color);

        if stand_pat >= beta {
            return beta;
        }

        if alpha < stand_pat {
            alpha = stand_pat;
        }

        // 深度限制
        if qs_depth >= QS_DEPTH_LIMIT {
            return stand_pat;
        }

        // 只搜索吃子走法
        let mut captures = self.get_captures(board, color);
        // MVV-LVA 排序
        captures.sort_by(|a, b| {
            self.mvv_lva_score(board, b)
                .cmp(&self.mvv_lva_score(board, a))
        });

        for mv in captures {
            let piece = match board.get_piece(mv.from_pos) {
                Some(p) => p,
                None => continue,
            };

            let was_hidden = piece.is_hidden;
            let captured = board.make_move(&mv);

            // 吃将
            if captured
                .as_ref()
                .is_some_and(|p| p.actual_type == Some(PieceType::King))
            {
                board.undo_move(&mv, captured, was_hidden);
                return MATE_SCORE - ply;
            }

            let score = -self.quiescence(
                board,
                -beta,
                -alpha,
                color.opposite(),
                ply + 1,
                qs_depth + 1,
            );

            board.undo_move(&mv, captured, was_hidden);

            if score >= beta {
                return beta;
            }

            if score > alpha {
                alpha = score;
            }
        }

        alpha
    }

    /// PVS 搜索
    #[allow(clippy::too_many_arguments)]
    fn pvs(
        &mut self,
        board: &mut Board,
        depth: i32,
        mut alpha: i32,
        beta: i32,
        color: Color,
        ply: i32,
        is_pv: bool,
    ) -> i32 {
        self.nodes_evaluated += 1;
        NODE_COUNT.fetch_add(1, AtomicOrdering::Relaxed);

        // 每 2000 节点检查时间
        if self.nodes_evaluated.is_multiple_of(2000) && self.is_time_up() {
            return alpha;
        }

        let alpha_orig = alpha;
        let hash = compute_hash(board);

        // TT 查找
        let tt_entry = self.tt.get(hash).copied();
        if let Some(entry) = tt_entry {
            if entry.depth >= depth as i8 && !is_pv {
                match entry.flag {
                    TTFlag::Exact => return entry.score,
                    TTFlag::LowerBound => alpha = alpha.max(entry.score),
                    TTFlag::UpperBound => {
                        if entry.score < beta {
                            let beta_new = beta.min(entry.score);
                            if alpha >= beta_new {
                                return entry.score;
                            }
                        }
                    }
                    TTFlag::None => {}
                }
                if alpha >= beta {
                    return entry.score;
                }
            }
        }

        let tt_move = tt_entry.and_then(|e| e.best_move);

        // 终局检查
        if board.find_king(color).is_none() {
            return -MATE_SCORE + ply;
        }
        if board.find_king(color.opposite()).is_none() {
            return MATE_SCORE - ply;
        }

        // 叶子节点 - 使用静态搜索
        if depth <= 0 {
            return self.quiescence(board, alpha, beta, color, ply, 0);
        }

        // 获取走法
        let legal_moves = board.get_legal_moves(color);
        if legal_moves.is_empty() {
            if board.is_in_check(color) {
                return -MATE_SCORE + ply;
            }
            return 0; // 和棋
        }

        // 走法排序
        let prev_best = if (depth as usize) < 64 {
            self.best_move_at_depth[depth as usize].map(|(m, _)| m)
        } else {
            None
        };
        let sorted_moves =
            self.order_moves(board, &legal_moves, color, ply as usize, tt_move, prev_best);

        let mut best_score = i32::MIN + 1;
        let mut best_move = None;
        let in_check = board.is_in_check(color);

        for (i, mv) in sorted_moves.iter().enumerate() {
            let piece = match board.get_piece(mv.from_pos) {
                Some(p) => p,
                None => continue,
            };

            let was_hidden = piece.is_hidden;
            let captured = board.make_move(mv);

            // 吃将
            if captured
                .as_ref()
                .is_some_and(|p| p.actual_type == Some(PieceType::King))
            {
                board.undo_move(mv, captured, was_hidden);
                return MATE_SCORE - ply;
            }

            // LMR (Late Move Reduction)
            let mut new_depth = depth - 1;
            if i >= LMR_FULL_DEPTH_MOVES
                && depth >= LMR_REDUCTION_LIMIT
                && captured.is_none()
                && !in_check
                && !was_hidden
            {
                let reduction = if i < 10 { 1 } else { 2 };
                new_depth = (depth - 1 - reduction).max(1);
            }

            // PVS 搜索
            let score = if i == 0 || !is_pv {
                -self.pvs(
                    board,
                    new_depth,
                    -beta,
                    -alpha,
                    color.opposite(),
                    ply + 1,
                    is_pv,
                )
            } else {
                // 窄窗口搜索
                let mut score = -self.pvs(
                    board,
                    new_depth,
                    -alpha - 1,
                    -alpha,
                    color.opposite(),
                    ply + 1,
                    false,
                );
                if alpha < score && score < beta {
                    // 重新搜索
                    score = -self.pvs(
                        board,
                        depth - 1,
                        -beta,
                        -score,
                        color.opposite(),
                        ply + 1,
                        true,
                    );
                }
                score
            };

            board.undo_move(mv, captured, was_hidden);

            if score > best_score {
                best_score = score;
                best_move = Some(*mv);
            }

            alpha = alpha.max(score);

            if alpha >= beta {
                // Beta cutoff
                if captured.is_none() {
                    self.update_killers(*mv, ply as usize);
                    self.update_history(mv, depth);
                }
                break;
            }
        }

        // 存储 TT
        let flag = if best_score <= alpha_orig {
            TTFlag::UpperBound
        } else if best_score >= beta {
            TTFlag::LowerBound
        } else {
            TTFlag::Exact
        };

        self.tt
            .store(hash, depth as i8, best_score, flag, best_move);

        best_score
    }

    /// 根节点搜索
    fn search_root_all(
        &mut self,
        board: &Board,
        legal_moves: &[JieqiMove],
        depth: u32,
        color: Color,
    ) -> Vec<(JieqiMove, i32)> {
        let hash = compute_hash(board);
        let tt_entry = self.tt.get(hash).copied();
        let tt_move = tt_entry.and_then(|e| e.best_move);

        let prev_best = if depth > 1 && ((depth - 1) as usize) < 64 {
            self.best_move_at_depth[(depth - 1) as usize].map(|(m, _)| m)
        } else {
            None
        };

        let sorted_moves = self.order_moves(board, legal_moves, color, 0, tt_move, prev_best);

        let mut results: Vec<(JieqiMove, i32)> = Vec::with_capacity(sorted_moves.len());
        let mut alpha = i32::MIN + 1;
        let beta = i32::MAX - 1;

        for (i, mv) in sorted_moves.iter().enumerate() {
            if self.is_time_up() {
                break;
            }

            let mut board_copy = board.clone();
            let captured = board_copy.make_move(mv);

            // 吃将
            if captured
                .as_ref()
                .is_some_and(|p| p.actual_type == Some(PieceType::King))
            {
                results.push((*mv, MATE_SCORE));
                continue;
            }

            // PVS 搜索
            let score = if i == 0 {
                -self.pvs(
                    &mut board_copy,
                    depth as i32 - 1,
                    -beta,
                    -alpha,
                    color.opposite(),
                    1,
                    true,
                )
            } else {
                // 窄窗口搜索
                let mut score = -self.pvs(
                    &mut board_copy,
                    depth as i32 - 1,
                    -alpha - 1,
                    -alpha,
                    color.opposite(),
                    1,
                    false,
                );
                if alpha < score && score < beta {
                    score = -self.pvs(
                        &mut board_copy,
                        depth as i32 - 1,
                        -beta,
                        -score,
                        color.opposite(),
                        1,
                        true,
                    );
                }
                score
            };

            results.push((*mv, score));
            alpha = alpha.max(score);
        }

        results
    }

    /// 迭代加深搜索
    fn iterative_deepening(&mut self, board: &Board) -> Vec<(JieqiMove, i32)> {
        let current_color = board.current_turn();
        let moves = board.get_legal_moves(current_color);
        if moves.is_empty() {
            return Vec::new();
        }

        self.start_time = Instant::now();
        self.best_move_at_depth.fill(None);
        self.nodes_evaluated = 0;

        let mut all_scores: Vec<(JieqiMove, i32)> = Vec::new();

        for depth in 1..=self.max_depth {
            // 检查时间限制（深度 > 1 时才检查，确保至少完成一层）
            if depth > 1 {
                if let Some(limit) = self.time_limit {
                    // 预留 70% 时间用于当前深度
                    if self.start_time.elapsed() >= limit.mul_f64(0.7) {
                        break;
                    }
                }
            }

            let scores = self.search_root_all(board, &moves, depth, current_color);

            // 只有完成整个深度才更新
            if scores.len() == moves.len() {
                all_scores = scores;

                // 按分数排序
                all_scores.sort_by(|a, b| b.1.cmp(&a.1));

                // 记录当前深度最佳走法
                if let Some(&(best_move, best_score)) = all_scores.first() {
                    if (depth as usize) < 64 {
                        self.best_move_at_depth[depth as usize] = Some((best_move, best_score));
                    }
                }
            }
        }

        all_scores
    }
}

/// 将内部分数归一化到 -1000 到 1000 范围
fn normalize_score(score: i32) -> f64 {
    // 将杀分数 (MATE_SCORE = 10000)
    if score >= MATE_SCORE - 100 {
        return 1000.0;
    }
    if score <= -(MATE_SCORE - 100) {
        return -1000.0;
    }

    // 普通分数：clamp 到 -999 到 999
    // 当前棋子价值范围大约 -5000 到 5000，缩放到 -999 到 999
    let normalized = (score as f64 / 5.0).clamp(-999.0, 999.0);
    normalized
}

impl AIStrategy for MusesAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        // 创建新实例避免可变借用问题
        let mut ai = MusesAI::new(&AIConfig {
            depth: self.max_depth,
            randomness: self.randomness,
            seed: None,
            time_limit: self.time_limit.map(|d| d.as_secs_f64()),
        });

        let results = ai.iterative_deepening(board);

        let mut scored: Vec<ScoredMove> = results
            .into_iter()
            .map(|(mv, score)| {
                let noise = if ai.randomness > 0.0 {
                    (ai.rng.gen::<f64>() * ai.randomness * 20.0) as i32
                } else {
                    0
                };
                ScoredMove {
                    mv,
                    score: normalize_score(score + noise),
                }
            })
            .collect();

        sort_and_truncate(&mut scored, n);
        scored
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_muses_basic() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let config = AIConfig {
            depth: 3,
            ..Default::default()
        };
        let ai = MusesAI::new(&config);
        let moves = ai.select_moves(&board, 5);
        assert!(!moves.is_empty());
    }

    #[test]
    fn test_muses_with_time_limit() {
        let fen = "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let config = AIConfig {
            depth: 3,
            time_limit: Some(0.5),
            ..Default::default()
        };
        let ai = MusesAI::new(&config);
        let start = Instant::now();
        let moves = ai.select_moves(&board, 3);
        let elapsed = start.elapsed();

        assert!(!moves.is_empty());
        assert!(elapsed.as_secs_f64() < 1.0); // 应该在时间限制内完成
    }

    #[test]
    fn test_muses_capture_preference() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let config = AIConfig {
            depth: 3,
            ..Default::default()
        };
        let ai = MusesAI::new(&config);
        let moves = ai.select_moves(&board, 1);
        assert!(!moves.is_empty());
        // 应该优先吃炮
        assert_eq!(moves[0].mv.to_fen_str(None), "e4e5");
    }
}
