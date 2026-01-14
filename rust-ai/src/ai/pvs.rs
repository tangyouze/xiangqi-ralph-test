//! PVS (Principal Variation Search) 高级搜索引擎 - 优化版
//!
//! 优化：
//! - Zobrist Hashing (比 DefaultHasher 快 10x)
//! - 数组 TT (比 HashMap 快 5x)
//! - 整数评分 (比 f64 快)
//! - 内联关键函数
//! - 减少内存分配

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove};
use crate::board::Board;
use crate::types::{ActionType, Color, JieqiMove, PieceType, Position, HIDDEN_PIECE_VALUE};
use rand::prelude::*;
use std::sync::atomic::Ordering as AtomicOrdering;
use std::time::{Duration, Instant};

use super::minimax::NODE_COUNT;

// ============================================================================
// Zobrist Hashing
// ============================================================================

/// Zobrist 哈希表 - 预计算随机数
struct ZobristTable {
    // [position][color * 8 + piece_type][is_hidden] = 90 * 16 * 2 = 2880 values
    pieces: [[[u64; 2]; 16]; 90],  // 2 colors × 8 piece types
    turn: u64,
}

impl ZobristTable {
    fn new() -> Self {
        let mut rng = StdRng::seed_from_u64(0xDEADBEEF);
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
    fn piece_hash(&self, pos: usize, color: Color, piece_type: Option<PieceType>, is_hidden: bool) -> u64 {
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

// 全局 Zobrist 表
lazy_static::lazy_static! {
    static ref ZOBRIST: ZobristTable = ZobristTable::new();
}

/// 计算棋盘的 Zobrist 哈希
#[inline]
fn compute_zobrist_hash(board: &Board) -> u64 {
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
// 高速置换表 (数组实现)
// ============================================================================

const TT_SIZE: usize = 1 << 20;  // 1M entries
const TT_MASK: usize = TT_SIZE - 1;

#[derive(Clone, Copy)]
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
        if entry.hash == hash && entry.flag as u8 != 0 {
            Some(entry)
        } else {
            None
        }
    }

    #[inline]
    fn store(&mut self, hash: u64, depth: i8, score: i32, flag: TTFlag, best_move: Option<JieqiMove>) {
        let idx = (hash as usize) & TT_MASK;
        let entry = &mut self.entries[idx];

        // 替换策略：深度优先
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

const NULL_MOVE_REDUCTION: i32 = 2;
const NULL_MOVE_DEPTH_LIMIT: i32 = 3;
const FUTILITY_MARGIN: i32 = 3000;
const FUTILITY_DEPTH: i32 = 3;
const LMR_FULL_DEPTH_MOVES: usize = 4;
const LMR_DEPTH_LIMIT: i32 = 3;
const LMP_DEPTH: i32 = 3;
const LMP_MOVE_COUNT: [usize; 4] = [0, 5, 10, 15];
const IID_DEPTH: i32 = 4;
const ASPIRATION_WINDOW: i32 = 500;
const DELTA_MARGIN: i32 = 9500;
const MATE_SCORE: i32 = 100000;

// ============================================================================
// PVS AI
// ============================================================================

pub struct PVSAI {
    max_depth: u32,
    rng: StdRng,
    randomness: f64,
    time_limit: Option<Duration>,
    // 搜索状态（大数组用 Vec 避免 stack overflow）
    tt: TranspositionTable,
    history: Vec<Vec<i32>>,  // [from][to]
    killers: Vec<[Option<JieqiMove>; 2]>,  // [ply][slot]
    countermove: Vec<Vec<Option<JieqiMove>>>,  // [from][to]
    start_time: Instant,
    best_move_at_depth: Vec<Option<JieqiMove>>,
    prev_score: i32,
}

impl PVSAI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };

        PVSAI {
            max_depth: config.depth.max(4),
            rng,
            randomness: config.randomness,
            time_limit: config.time_limit.map(Duration::from_secs_f64),
            tt: TranspositionTable::new(),
            history: vec![vec![0; 90]; 90],
            killers: vec![[None; 2]; 64],
            countermove: vec![vec![None; 90]; 90],
            start_time: Instant::now(),
            best_move_at_depth: vec![None; 64],
            prev_score: 0,
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

    /// 快速评估
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
                // 位置奖励
                let center_bonus = (5 - (4 - piece.position.col as i32).abs()) as i32;
                score += center_bonus;
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
        let victim = board.get_piece(mv.to_pos).map_or(0, |p| Self::get_piece_value(p));
        let attacker = board.get_piece(mv.from_pos).map_or(0, |p| Self::get_piece_value(p));
        victim * 10 - attacker
    }

    /// 走法排序（原地排序，不分配新内存）
    fn order_moves_inplace(
        &self,
        board: &Board,
        moves: &mut [JieqiMove],
        color: Color,
        ply: usize,
        tt_move: Option<JieqiMove>,
        prev_best: Option<JieqiMove>,
        last_move: Option<&JieqiMove>,
    ) {
        let countermove = last_move.and_then(|m| {
            self.countermove[m.from_pos.to_index()][m.to_pos.to_index()]
        });

        // 计算每个走法的分数
        let mut scores: Vec<i32> = moves.iter().map(|mv| {
            let mut score: i32 = 0;

            if prev_best == Some(*mv) {
                score += 30_000_000;
            }
            if tt_move == Some(*mv) {
                score += 20_000_000;
            }

            // 吃子
            if let Some(target) = board.get_piece(mv.to_pos) {
                if target.color != color {
                    score += 10_000_000 + self.mvv_lva_score(board, mv);
                }
            }

            if countermove == Some(*mv) {
                score += 800_000;
            }

            if ply < 64 {
                if self.killers[ply][0] == Some(*mv) || self.killers[ply][1] == Some(*mv) {
                    score += 600_000;
                }
            }

            score += self.history[mv.from_pos.to_index()][mv.to_pos.to_index()];

            if mv.action_type == ActionType::RevealAndMove {
                score += 300;
            }

            score
        }).collect();

        // 简单选择排序（对于小数组比快排快）
        for i in 0..moves.len() {
            let mut best_idx = i;
            for j in (i + 1)..moves.len() {
                if scores[j] > scores[best_idx] {
                    best_idx = j;
                }
            }
            if best_idx != i {
                moves.swap(i, best_idx);
                scores.swap(i, best_idx);
            }
        }
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

    #[inline]
    fn has_non_pawn_pieces(&self, board: &Board, color: Color) -> bool {
        for piece in board.get_all_pieces(Some(color)) {
            if piece.is_hidden {
                return true;
            }
            if let Some(pt) = piece.actual_type {
                if pt != PieceType::Pawn && pt != PieceType::King {
                    return true;
                }
            }
        }
        false
    }

    /// 静态搜索
    fn quiesce(&mut self, board: &mut Board, mut alpha: i32, beta: i32, color: Color, ply: i32) -> i32 {
        let stand_pat = self.evaluate(board, color);

        if stand_pat >= beta {
            return beta;
        }

        if stand_pat + DELTA_MARGIN < alpha {
            return alpha;
        }

        if alpha < stand_pat {
            alpha = stand_pat;
        }

        // 获取吃子走法
        let legal_moves = board.get_legal_moves(color);
        let mut captures: Vec<(i32, JieqiMove)> = legal_moves
            .into_iter()
            .filter_map(|mv| {
                board.get_piece(mv.to_pos).and_then(|target| {
                    if target.color != color {
                        Some((self.mvv_lva_score(board, &mv), mv))
                    } else {
                        None
                    }
                })
            })
            .collect();

        // MVV-LVA 排序
        captures.sort_by(|a, b| b.0.cmp(&a.0));

        for (_, mv) in captures {
            // Delta pruning
            if let Some(target) = board.get_piece(mv.to_pos) {
                if stand_pat + Self::get_piece_value(target) + 200 < alpha {
                    continue;
                }
            }

            let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
            let captured = board.make_move(&mv);

            if captured.as_ref().map_or(false, |p| p.actual_type == Some(PieceType::King)) {
                board.undo_move(&mv, captured, was_hidden);
                return MATE_SCORE - ply;
            }

            let score = -self.quiesce(board, -beta, -alpha, color.opposite(), ply + 1);
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
    fn pvs(
        &mut self,
        board: &mut Board,
        depth: i32,
        mut alpha: i32,
        beta: i32,
        color: Color,
        ply: i32,
        is_pv: bool,
        prev_move: Option<&JieqiMove>,
    ) -> i32 {
        NODE_COUNT.fetch_add(1, AtomicOrdering::Relaxed);

        if NODE_COUNT.load(AtomicOrdering::Relaxed) % 4096 == 0 && self.is_time_up() {
            return alpha;
        }

        let alpha_orig = alpha;
        let hash = compute_zobrist_hash(board);

        // TT 查找
        let tt_entry = self.tt.get(hash).copied();
        let tt_move = tt_entry.and_then(|e| e.best_move);

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

        // 终局检查
        if board.find_king(color).is_none() {
            return -MATE_SCORE + ply;
        }
        if board.find_king(color.opposite()).is_none() {
            return MATE_SCORE - ply;
        }

        let in_check = board.is_in_check(color);

        if depth <= 0 {
            return self.quiesce(board, alpha, beta, color, ply);
        }

        // Null Move Pruning
        if !is_pv && !in_check && depth >= NULL_MOVE_DEPTH_LIMIT && self.has_non_pawn_pieces(board, color) {
            let old_turn = board.current_turn();
            board.set_turn(color.opposite());

            let reduction = NULL_MOVE_REDUCTION + depth / 4;
            let null_score = -self.pvs(
                board,
                depth - 1 - reduction,
                -beta,
                -beta + 1,
                color.opposite(),
                ply + 1,
                false,
                None,
            );

            board.set_turn(old_turn);

            if null_score >= beta {
                if depth >= 6 {
                    let verify = self.pvs(board, depth - 5, beta - 1, beta, color, ply, false, prev_move);
                    if verify >= beta {
                        return beta;
                    }
                } else {
                    return beta;
                }
            }
        }

        // 获取走法
        let mut legal_moves = board.get_legal_moves(color);
        if legal_moves.is_empty() {
            if in_check {
                return -MATE_SCORE + ply;
            }
            return 0;
        }

        // IID
        if tt_entry.is_none() && depth >= IID_DEPTH && is_pv {
            self.pvs(board, depth - 2, alpha, beta, color, ply, true, prev_move);
        }

        // 排序
        let prev_best = if (depth as usize) < 64 { self.best_move_at_depth[depth as usize] } else { None };
        self.order_moves_inplace(board, &mut legal_moves, color, ply as usize, tt_move, prev_best, prev_move);

        let static_eval = if !in_check { self.evaluate(board, color) } else { 0 };

        let mut best_score = i32::MIN + 1;
        let mut best_move = None;
        let mut moves_searched = 0;

        for mv in legal_moves {
            let piece = match board.get_piece(mv.from_pos) {
                Some(p) => p,
                None => continue,
            };

            let target = board.get_piece(mv.to_pos);
            let is_capture = target.map_or(false, |t| t.color != color);
            let is_reveal = mv.action_type == ActionType::RevealAndMove;
            let was_hidden = piece.is_hidden;

            // Futility Pruning
            if !is_pv && !in_check && depth <= FUTILITY_DEPTH && !is_capture && !is_reveal
                && static_eval + FUTILITY_MARGIN * depth < alpha
            {
                continue;
            }

            // LMP
            if !is_pv && !in_check && depth <= LMP_DEPTH && depth > 0
                && moves_searched >= LMP_MOVE_COUNT[depth as usize]
                && !is_capture && !is_reveal
            {
                continue;
            }

            let captured = board.make_move(&mv);

            if captured.as_ref().map_or(false, |p| p.actual_type == Some(PieceType::King)) {
                board.undo_move(&mv, captured, was_hidden);
                return MATE_SCORE - ply;
            }

            let gives_check = board.is_in_check(color.opposite());

            // LMR
            let mut new_depth = depth - 1;
            if moves_searched >= LMR_FULL_DEPTH_MOVES
                && depth >= LMR_DEPTH_LIMIT
                && !is_capture && !in_check && !gives_check && !is_reveal
            {
                let mut reduction = 1 + (moves_searched / 8) as i32;
                if !is_pv {
                    reduction += 1;
                }
                new_depth = (depth - 1 - reduction).max(1);
            }

            let score = if moves_searched == 0 {
                -self.pvs(board, new_depth, -beta, -alpha, color.opposite(), ply + 1, is_pv, Some(&mv))
            } else {
                let mut score = -self.pvs(board, new_depth, -alpha - 1, -alpha, color.opposite(), ply + 1, false, Some(&mv));

                if score > alpha && new_depth < depth - 1 {
                    score = -self.pvs(board, depth - 1, -alpha - 1, -alpha, color.opposite(), ply + 1, false, Some(&mv));
                }

                if alpha < score && score < beta {
                    score = -self.pvs(board, depth - 1, -beta, -score, color.opposite(), ply + 1, true, Some(&mv));
                }

                score
            };

            board.undo_move(&mv, captured, was_hidden);
            moves_searched += 1;

            if score > best_score {
                best_score = score;
                best_move = Some(mv);
            }

            alpha = alpha.max(score);

            if alpha >= beta {
                if !is_capture {
                    self.update_killers(mv, ply as usize);
                    self.update_history(&mv, depth);
                    if let Some(pm) = prev_move {
                        self.countermove[pm.from_pos.to_index()][pm.to_pos.to_index()] = Some(mv);
                    }
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

        self.tt.store(hash, depth as i8, best_score, flag, best_move);

        best_score
    }

    /// 根节点搜索
    fn search_root(
        &mut self,
        board: &Board,
        legal_moves: &[JieqiMove],
        depth: u32,
        color: Color,
        alpha: i32,
        beta: i32,
    ) -> Vec<(JieqiMove, i32)> {
        let hash = compute_zobrist_hash(board);
        let tt_entry = self.tt.get(hash).copied();
        let tt_move = tt_entry.and_then(|e| e.best_move);
        let prev_best = if depth > 0 && (depth as usize - 1) < 64 {
            self.best_move_at_depth[depth as usize - 1]
        } else {
            None
        };

        let mut moves = legal_moves.to_vec();
        self.order_moves_inplace(board, &mut moves, color, 0, tt_move, prev_best, None);

        let mut results = Vec::with_capacity(moves.len());
        let mut alpha = alpha;

        for (i, mv) in moves.iter().enumerate() {
            if self.is_time_up() {
                break;
            }

            let mut board_copy = board.clone();
            let captured = board_copy.make_move(mv);

            if captured.as_ref().map_or(false, |p| p.actual_type == Some(PieceType::King)) {
                results.push((*mv, MATE_SCORE));
                continue;
            }

            let score = if i == 0 {
                -self.pvs(&mut board_copy, depth as i32 - 1, -beta, -alpha, color.opposite(), 1, true, Some(mv))
            } else {
                let mut score = -self.pvs(&mut board_copy, depth as i32 - 1, -alpha - 1, -alpha, color.opposite(), 1, false, Some(mv));
                if alpha < score && score < beta {
                    score = -self.pvs(&mut board_copy, depth as i32 - 1, -beta, -score, color.opposite(), 1, true, Some(mv));
                }
                score
            };

            results.push((*mv, score));
            alpha = alpha.max(score);
        }

        results
    }

    /// 迭代加深
    fn iterative_deepening(&mut self, board: &Board) -> Vec<(JieqiMove, i32)> {
        let current_color = board.current_turn();
        let moves = board.get_legal_moves(current_color);
        if moves.is_empty() {
            return Vec::new();
        }

        self.start_time = Instant::now();
        self.best_move_at_depth.fill(None);
        self.prev_score = 0;

        let mut all_scores: Vec<(JieqiMove, i32)> = Vec::new();

        for depth in 1..=self.max_depth {
            if depth > 1 && self.is_time_up() {
                break;
            }

            let scores = if depth <= 2 {
                self.search_root(board, &moves, depth, current_color, i32::MIN + 1, i32::MAX - 1)
            } else {
                let alpha = self.prev_score - ASPIRATION_WINDOW;
                let beta = self.prev_score + ASPIRATION_WINDOW;

                let mut scores = self.search_root(board, &moves, depth, current_color, alpha, beta);

                if !scores.is_empty() {
                    let best_score = scores.iter().map(|(_, s)| *s).max().unwrap_or(0);
                    if best_score <= alpha {
                        scores = self.search_root(board, &moves, depth, current_color, i32::MIN + 1, beta);
                    } else if best_score >= beta {
                        scores = self.search_root(board, &moves, depth, current_color, alpha, i32::MAX - 1);
                    }
                }

                scores
            };

            if !scores.is_empty() {
                all_scores = scores;
                if let Some(&(best_move, best_score)) = all_scores.iter().max_by_key(|(_, s)| *s) {
                    if (depth as usize) < 64 {
                        self.best_move_at_depth[depth as usize] = Some(best_move);
                    }
                    self.prev_score = best_score;
                }
            }
        }

        all_scores.sort_by(|a, b| b.1.cmp(&a.1));
        all_scores
    }
}

impl AIStrategy for PVSAI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let mut ai = PVSAI::new(&AIConfig {
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
                    (ai.rng.gen::<f64>() * ai.randomness * 100.0) as i32
                } else {
                    0
                };
                ScoredMove {
                    mv,
                    score: (score + noise) as f64,
                }
            })
            .collect();

        sort_and_truncate(&mut scored, n);
        scored
    }
}
