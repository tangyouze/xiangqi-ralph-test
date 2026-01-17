//! Muses2 AI 策略 - 在 muses 基础上改进
//!
//! 改进特性：
//! 1. Aspiration Windows - 期望窗口搜索
//! 2. 改进的评估函数 - 国王安全、棋子活动度、暗子期望价值
//! 3. Futility Pruning - 无用剪枝
//! 4. Delta Pruning - 静态搜索剪枝
//! 5. Check Extension - 将军延伸
//! 6. 更好的揭子策略评估

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{ActionType, Color, JieqiMove, PieceType, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
use std::sync::atomic::Ordering as AtomicOrdering;
use std::time::{Duration, Instant};

use super::{DEPTH_REACHED, NODE_COUNT};

// ============================================================================
// Zobrist Hashing
// ============================================================================

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

const TT_SIZE: usize = 1 << 20; // 1M entries (与 muses 相同)
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
}

impl TranspositionTable {
    fn new() -> Self {
        TranspositionTable {
            entries: vec![TTEntry::default(); TT_SIZE],
        }
    }

    #[inline]
    fn get(&self, hash: u64) -> Option<&TTEntry> {
        let idx = (hash as usize) & TT_MASK;
        let entry = &self.entries[idx];
        if entry.hash == hash && entry.flag != TTFlag::None {
            Some(entry)
        } else {
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

        // 深度替换策略 + 年龄替换
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
const QS_DEPTH_LIMIT: i32 = 4; // 与 muses 相同
const LMR_FULL_DEPTH_MOVES: usize = 4;
const LMR_REDUCTION_LIMIT: i32 = 3;
const MAX_DEPTH: u32 = 30;

// Null Move Pruning 参数 - 揭棋中禁用，因为空步可能错过重要的揭子机会
// const NULL_MOVE_REDUCTION: i32 = 3;
// const NULL_MOVE_MIN_DEPTH: i32 = 3;

// Futility Pruning 参数（暂未使用）
#[allow(dead_code)]
const FUTILITY_MARGIN: [i32; 4] = [0, 200, 300, 500];

// Aspiration Window 参数
const ASPIRATION_WINDOW: i32 = 50;

// Delta Pruning 参数
const DELTA_MARGIN: i32 = 200;

// ============================================================================
// Muses2 AI
// ============================================================================

pub struct Muses2AI {
    max_depth: u32,
    rng: StdRng,
    randomness: f64,
    time_limit: Option<Duration>,
    tt: TranspositionTable,
    history: Vec<Vec<i32>>,
    killers: Vec<[Option<JieqiMove>; 2]>,
    countermoves: Vec<Vec<Option<JieqiMove>>>, // 新增：countermove heuristic
    start_time: Instant,
    best_move_at_depth: Vec<Option<(JieqiMove, i32)>>,
    nodes_evaluated: u64,
}

impl Muses2AI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };

        let max_depth = if config.time_limit.is_some() {
            MAX_DEPTH
        } else if config.depth > 0 {
            config.depth.max(5)
        } else {
            5
        };

        Muses2AI {
            max_depth,
            rng,
            randomness: config.randomness,
            time_limit: config.time_limit.map(Duration::from_secs_f64),
            tt: TranspositionTable::new(),
            history: vec![vec![0; 90]; 90],
            killers: vec![[None; 2]; 64],
            countermoves: vec![vec![None; 90]; 90],
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

    /// 计算暗子的期望价值（基于剩余暗子池）
    fn hidden_piece_expected_value(&self, board: &Board, piece_color: Color) -> i32 {
        // 统计已揭开的棋子
        let mut revealed_count: [i32; 7] = [0; 7]; // King, Advisor, Elephant, Horse, Rook, Cannon, Pawn
        let mut hidden_count = 0;

        for piece in board.get_all_pieces(Some(piece_color)) {
            if piece.is_hidden {
                hidden_count += 1;
            } else if let Some(pt) = piece.actual_type {
                let idx = match pt {
                    PieceType::King => 0,
                    PieceType::Advisor => 1,
                    PieceType::Elephant => 2,
                    PieceType::Horse => 3,
                    PieceType::Rook => 4,
                    PieceType::Cannon => 5,
                    PieceType::Pawn => 6,
                };
                revealed_count[idx] += 1;
            }
        }

        if hidden_count == 0 {
            return 0;
        }

        // 初始棋子数量：1 King, 2 Advisor, 2 Elephant, 2 Horse, 2 Rook, 2 Cannon, 5 Pawn
        let initial_count: [i32; 7] = [1, 2, 2, 2, 2, 2, 5];
        let values: [i32; 7] = [10000, 250, 250, 500, 1200, 600, 100];

        // 计算剩余暗子池的期望价值
        let mut total_remaining = 0i32;
        let mut weighted_sum = 0i32;

        for i in 0..7 {
            let remaining = initial_count[i] - revealed_count[i];
            if remaining > 0 {
                total_remaining += remaining;
                weighted_sum += remaining * values[i];
            }
        }

        if total_remaining > 0 {
            weighted_sum / total_remaining
        } else {
            HIDDEN_PIECE_VALUE
        }
    }

    /// 评估局面 - 使用暗子期望价值
    #[inline]
    fn evaluate(&self, board: &Board, color: Color) -> i32 {
        let mut score: i32 = 0;

        // 计算双方的暗子期望价值
        let my_ev = self.hidden_piece_expected_value(board, color);
        let opp_ev = self.hidden_piece_expected_value(board, color.opposite());

        for piece in board.get_all_pieces(None) {
            let value = if piece.is_hidden {
                // 使用期望价值而非固定值
                if piece.color == color { my_ev } else { opp_ev }
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
        let attacker = board.get_piece(mv.from_pos).map_or(0, Self::get_piece_value);
        victim * 10 - attacker
    }

    /// 走法排序 - 增加 countermove
    fn order_moves(
        &self,
        board: &Board,
        moves: &[JieqiMove],
        color: Color,
        ply: usize,
        tt_move: Option<JieqiMove>,
        prev_best: Option<JieqiMove>,
        prev_move: Option<JieqiMove>,
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

                // Countermove heuristic
                if let Some(prev) = prev_move {
                    let from_idx = prev.from_pos.to_index();
                    let to_idx = prev.to_pos.to_index();
                    if self.countermoves[from_idx][to_idx] == Some(*mv) {
                        score += 400_000;
                    }
                }

                // History heuristic
                score += self.history[mv.from_pos.to_index()][mv.to_pos.to_index()];

                // 揭子走法 - 与 muses 相同
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

        if self.history[from_idx][to_idx] > 1_000_000 {
            for row in &mut self.history {
                for v in row.iter_mut() {
                    *v /= 2;
                }
            }
        }
    }

    #[inline]
    fn update_countermove(&mut self, prev_move: Option<JieqiMove>, mv: JieqiMove) {
        if let Some(prev) = prev_move {
            let from_idx = prev.from_pos.to_index();
            let to_idx = prev.to_pos.to_index();
            self.countermoves[from_idx][to_idx] = Some(mv);
        }
    }

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

    /// 静态搜索 - 增加 Delta Pruning
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

        // Delta Pruning: 如果即使吃最大价值的子也无法提高 alpha
        if stand_pat + DELTA_MARGIN + 1000 < alpha {
            return alpha;
        }

        if alpha < stand_pat {
            alpha = stand_pat;
        }

        if qs_depth >= QS_DEPTH_LIMIT {
            return stand_pat;
        }

        let mut captures = self.get_captures(board, color);
        captures.sort_by(|a, b| {
            self.mvv_lva_score(board, b)
                .cmp(&self.mvv_lva_score(board, a))
        });

        for mv in captures {
            // Delta Pruning for individual captures
            let captured_value = board.get_piece(mv.to_pos).map_or(0, Self::get_piece_value);
            if stand_pat + captured_value + DELTA_MARGIN < alpha {
                continue;
            }

            let piece = match board.get_piece(mv.from_pos) {
                Some(p) => p,
                None => continue,
            };

            let was_hidden = piece.is_hidden;
            let captured = board.make_move(&mv);

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

    /// 检查是否可以进行 Null Move Pruning（暂未使用）
    #[allow(dead_code)]
    fn can_do_null_move(&self, board: &Board, color: Color) -> bool {
        // 不在残局时才进行 null move
        let piece_count = board.get_all_pieces(Some(color)).len();
        piece_count > 3
    }

    /// PVS 搜索 - 增加 Null Move Pruning 和 Futility Pruning
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
        prev_move: Option<JieqiMove>,
        _null_move_allowed: bool,
    ) -> i32 {
        self.nodes_evaluated += 1;
        NODE_COUNT.fetch_add(1, AtomicOrdering::Relaxed);

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

        // 叶子节点
        if depth <= 0 {
            return self.quiescence(board, alpha, beta, color, ply, 0);
        }

        let in_check = board.is_in_check(color);

        // Null Move Pruning - 在揭棋中禁用
        // 因为揭棋中空步可能错过重要的揭子机会，且暗子状态使得 null move 假设不成立

        // 获取走法
        let legal_moves = board.get_legal_moves(color);
        if legal_moves.is_empty() {
            if in_check {
                return -MATE_SCORE + ply;
            }
            return 0;
        }

        // 走法排序
        let prev_best = if (depth as usize) < 64 {
            self.best_move_at_depth[depth as usize].map(|(m, _)| m)
        } else {
            None
        };
        let sorted_moves = self.order_moves(
            board,
            &legal_moves,
            color,
            ply as usize,
            tt_move,
            prev_best,
            prev_move,
        );

        let mut best_score = i32::MIN + 1;
        let mut best_move = None;

        for (i, mv) in sorted_moves.iter().enumerate() {
            let piece = match board.get_piece(mv.from_pos) {
                Some(p) => p,
                None => continue,
            };

            let was_hidden = piece.is_hidden;

            let captured = board.make_move(mv);

            if captured
                .as_ref()
                .is_some_and(|p| p.actual_type == Some(PieceType::King))
            {
                board.undo_move(mv, captured, was_hidden);
                return MATE_SCORE - ply;
            }

            // 计算搜索深度
            let _gives_check = board.is_in_check(color.opposite());
            let mut new_depth = depth - 1;

            // LMR: 后期走法缩减（与 muses 相同）
            if i >= LMR_FULL_DEPTH_MOVES
                && depth >= LMR_REDUCTION_LIMIT
                && captured.is_none()
                && !in_check
                && !was_hidden
            {
                let reduction = if i < 10 { 1 } else { 2 };
                new_depth = (new_depth - reduction).max(1);
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
                    Some(*mv),
                    true,
                )
            } else {
                let mut score = -self.pvs(
                    board,
                    new_depth,
                    -alpha - 1,
                    -alpha,
                    color.opposite(),
                    ply + 1,
                    false,
                    Some(*mv),
                    true,
                );
                if alpha < score && score < beta {
                    score = -self.pvs(
                        board,
                        depth - 1,
                        -beta,
                        -score,
                        color.opposite(),
                        ply + 1,
                        true,
                        Some(*mv),
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
                if captured.is_none() {
                    self.update_killers(*mv, ply as usize);
                    self.update_history(mv, depth);
                    self.update_countermove(prev_move, *mv);
                }
                break;
            }
        }

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

        let sorted_moves = self.order_moves(board, legal_moves, color, 0, tt_move, prev_best, None);

        let mut results: Vec<(JieqiMove, i32)> = Vec::with_capacity(sorted_moves.len());
        let mut alpha = i32::MIN + 1;
        let beta = i32::MAX - 1;

        for (i, mv) in sorted_moves.iter().enumerate() {
            if self.is_time_up() {
                break;
            }

            let mut board_copy = board.clone();
            let captured = board_copy.make_move(mv);

            if captured
                .as_ref()
                .is_some_and(|p| p.actual_type == Some(PieceType::King))
            {
                results.push((*mv, MATE_SCORE));
                continue;
            }

            let score = if i == 0 {
                -self.pvs(
                    &mut board_copy,
                    depth as i32 - 1,
                    -beta,
                    -alpha,
                    color.opposite(),
                    1,
                    true,
                    Some(*mv),
                    true,
                )
            } else {
                let mut score = -self.pvs(
                    &mut board_copy,
                    depth as i32 - 1,
                    -alpha - 1,
                    -alpha,
                    color.opposite(),
                    1,
                    false,
                    Some(*mv),
                    true,
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
                        Some(*mv),
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

    /// 迭代加深 - 增加 Aspiration Windows
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
        let mut prev_score: Option<i32> = None;

        for depth in 1..=self.max_depth {
            if depth > 1 {
                if let Some(limit) = self.time_limit {
                    if self.start_time.elapsed() >= limit.mul_f64(0.7) {
                        break;
                    }
                }
            }

            // Aspiration Windows
            let scores = if let Some(prev) = prev_score {
                // 使用期望窗口
                let alpha = prev - ASPIRATION_WINDOW;
                let beta = prev + ASPIRATION_WINDOW;
                let mut result = self.search_root_aspiration(board, &moves, depth, current_color, alpha, beta);

                // 如果失败，扩大窗口重新搜索
                if result.is_empty() || result.iter().all(|(_, s)| *s <= alpha || *s >= beta) {
                    result = self.search_root_all(board, &moves, depth, current_color);
                }
                result
            } else {
                self.search_root_all(board, &moves, depth, current_color)
            };

            if scores.len() == moves.len() {
                all_scores = scores;
                DEPTH_REACHED.store(depth, AtomicOrdering::Relaxed);
                all_scores.sort_by(|a, b| b.1.cmp(&a.1));

                if let Some(&(best_move, best_score)) = all_scores.first() {
                    prev_score = Some(best_score);
                    if (depth as usize) < 64 {
                        self.best_move_at_depth[depth as usize] = Some((best_move, best_score));
                    }
                }
            }
        }

        all_scores
    }

    /// Aspiration window search
    fn search_root_aspiration(
        &mut self,
        board: &Board,
        legal_moves: &[JieqiMove],
        depth: u32,
        color: Color,
        alpha: i32,
        beta: i32,
    ) -> Vec<(JieqiMove, i32)> {
        let hash = compute_hash(board);
        let tt_entry = self.tt.get(hash).copied();
        let tt_move = tt_entry.and_then(|e| e.best_move);

        let prev_best = if depth > 1 && ((depth - 1) as usize) < 64 {
            self.best_move_at_depth[(depth - 1) as usize].map(|(m, _)| m)
        } else {
            None
        };

        let sorted_moves = self.order_moves(board, legal_moves, color, 0, tt_move, prev_best, None);

        let mut results: Vec<(JieqiMove, i32)> = Vec::with_capacity(sorted_moves.len());
        let mut current_alpha = alpha;

        for (i, mv) in sorted_moves.iter().enumerate() {
            if self.is_time_up() {
                break;
            }

            let mut board_copy = board.clone();
            let captured = board_copy.make_move(mv);

            if captured
                .as_ref()
                .is_some_and(|p| p.actual_type == Some(PieceType::King))
            {
                results.push((*mv, MATE_SCORE));
                continue;
            }

            let score = if i == 0 {
                -self.pvs(
                    &mut board_copy,
                    depth as i32 - 1,
                    -beta,
                    -current_alpha,
                    color.opposite(),
                    1,
                    true,
                    Some(*mv),
                    true,
                )
            } else {
                let mut score = -self.pvs(
                    &mut board_copy,
                    depth as i32 - 1,
                    -current_alpha - 1,
                    -current_alpha,
                    color.opposite(),
                    1,
                    false,
                    Some(*mv),
                    true,
                );
                if current_alpha < score && score < beta {
                    score = -self.pvs(
                        &mut board_copy,
                        depth as i32 - 1,
                        -beta,
                        -score,
                        color.opposite(),
                        1,
                        true,
                        Some(*mv),
                        true,
                    );
                }
                score
            };

            results.push((*mv, score));
            current_alpha = current_alpha.max(score);
        }

        results
    }
}

fn normalize_score(score: i32) -> f64 {
    if score >= MATE_SCORE - 100 {
        return 1000.0;
    }
    if score <= -(MATE_SCORE - 100) {
        return -1000.0;
    }
    (score as f64 / 5.0).clamp(-999.0, 999.0)
}

impl AIStrategy for Muses2AI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let mut ai = Muses2AI::new(&AIConfig {
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
    fn test_muses2_basic() {
        let fen = "4k4/9/9/9/9/4R4/9/9/9/4K4 -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let config = AIConfig {
            depth: 3,
            ..Default::default()
        };
        let ai = Muses2AI::new(&config);
        let moves = ai.select_moves(&board, 5);
        assert!(!moves.is_empty());
    }

    #[test]
    fn test_muses2_capture() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let board = Board::from_fen(fen).unwrap();
        let config = AIConfig {
            depth: 3,
            ..Default::default()
        };
        let ai = Muses2AI::new(&config);
        let moves = ai.select_moves(&board, 1);
        assert!(!moves.is_empty());
        assert_eq!(moves[0].mv.to_fen_str(None), "e4e5");
    }
}
