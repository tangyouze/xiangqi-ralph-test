//! IT3 (Iterative Deepening v3) - Expectimax 概率处理 + 优化
//!
//! ## 核心特点
//! - 揭子走法使用 Chance 节点处理概率
//! - Negamax 框架 + Alpha-Beta 剪枝
//!
//! ## 评估函数设计
//! 内部总是计算"红方价值 - 黑方价值"，最后根据视角翻转符号。
//! 这样所有变量都是 red/black，避免 my/opp 的混淆。
//!
//! ```text
//! evaluate(board, Red)   →  raw_score
//! evaluate(board, Black) → -raw_score
//! ```
//!
//! 暗子期望值按颜色固定计算：
//! - red_hidden_ev: 红方暗子池的期望价值
//! - black_hidden_ev: 黑方暗子池的期望价值
//!
//! 吃子潜力：
//! - 红方吃黑方 → 被吃暗子用 black_hidden_ev
//! - 黑方吃红方 → 被吃暗子用 red_hidden_ev

mod eval;

// 内部使用（公开类型由 it2 导出，it3 不重复导出）
use eval::{get_pst_score, hidden_position_bonus, MATE_SCORE, PLY_PENALTY};
use eval::{EvalDetail, HiddenPieceDistribution, PieceEval};

use super::{sort_and_truncate, AIConfig, AIStrategy, ScoredMove, DEPTH_REACHED, NODE_COUNT};
use crate::board::Board;
use crate::types::{ActionType, Color, GameResult, JieqiMove, PieceType};
use rand::prelude::*;
use std::cell::Cell;
use std::cmp::Ordering as CmpOrdering;
use std::sync::atomic::Ordering as AtomicOrdering;
use std::time::{Duration, Instant};

/// 搜索上下文（减少参数传递）
#[derive(Clone, Copy)]
struct SearchContext {
    /// 剩余搜索深度
    depth: i32,
    /// 从根节点开始的步数
    ply: i32,
    /// Alpha-Beta 窗口
    alpha: f64,
    beta: f64,
    /// POV 视角（初始行棋方），分数始终相对于此颜色
    pov_color: Color,
}

impl SearchContext {
    fn new(depth: i32, pov_color: Color) -> Self {
        Self {
            depth,
            ply: 0,
            alpha: f64::NEG_INFINITY,
            beta: f64::INFINITY,
            pov_color,
        }
    }

    /// 进入下一层（固定 POV，不翻转窗口）
    fn next_ply(&self) -> Self {
        Self {
            depth: self.depth - 1,
            ply: self.ply + 1,
            alpha: self.alpha,
            beta: self.beta,
            pov_color: self.pov_color,
        }
    }
}

/// IT2 AI - Expectimax 搜索
pub struct IT3AI {
    max_depth: u32,
    rng: StdRng,
    randomness: f64,
    time_limit: Option<Duration>,
    /// 搜索开始时间（用于内部超时检查）
    start_time: Cell<Option<Instant>>,
}

impl IT3AI {
    pub fn new(config: &AIConfig) -> Self {
        let rng = match config.seed {
            Some(s) => StdRng::seed_from_u64(s),
            None => StdRng::from_entropy(),
        };
        // 如果设置了时间限制，允许无限加深；否则使用配置的深度
        let max_depth = if config.time_limit.is_some() {
            50
        } else {
            config.depth
        };
        IT3AI {
            max_depth,
            rng,
            randomness: config.randomness,
            time_limit: config.time_limit.map(Duration::from_secs_f64),
            start_time: Cell::new(None),
        }
    }

    /// 静态评估函数（公开接口）
    pub fn evaluate_static(board: &Board, color: Color) -> f64 {
        let ai = IT3AI::new(&AIConfig::default());
        ai.evaluate(board, color)
    }

    /// 详细评估（返回各分项）
    pub fn evaluate_detail(board: &Board, color: Color) -> EvalDetail {
        let ai = IT3AI::new(&AIConfig::default());
        ai.evaluate_breakdown(board, color)
    }

    /// 检查是否超时
    #[inline]
    fn is_timeout(&self) -> bool {
        if let (Some(limit), Some(start)) = (self.time_limit, self.start_time.get()) {
            start.elapsed() >= limit
        } else {
            false
        }
    }

    /// 详细评估（返回各分项）
    fn evaluate_breakdown(&self, board: &Board, color: Color) -> EvalDetail {
        // 按颜色固定计算暗子期望
        let red_hidden_ev =
            HiddenPieceDistribution::from_board(board, Color::Red).expected_value() as f64;
        let black_hidden_ev =
            HiddenPieceDistribution::from_board(board, Color::Black).expected_value() as f64;

        let mut material_red = 0.0;
        let mut material_black = 0.0;
        let mut pst_red = 0.0;
        let mut pst_black = 0.0;
        let mut hidden_value_red = 0.0;
        let mut hidden_value_black = 0.0;
        let mut pieces: Vec<PieceEval> = Vec::new();

        for piece in board.get_all_pieces(None) {
            let pos = piece.position;
            let pos_str = format!("{}{}", (b'a' + pos.col as u8) as char, pos.row);
            let color_str = if piece.color == Color::Red {
                "red"
            } else {
                "black"
            };

            if piece.is_hidden {
                // 暗子：期望值 + 位置加成
                let ev = if piece.color == Color::Red {
                    red_hidden_ev
                } else {
                    black_hidden_ev
                };
                let position_bonus = piece
                    .movement_type
                    .map(|mt| hidden_position_bonus(mt, pos.col) as f64)
                    .unwrap_or(0.0);
                let value = ev + position_bonus;

                pieces.push(PieceEval {
                    position: pos_str,
                    color: color_str.to_string(),
                    piece_type: "hidden".to_string(),
                    is_hidden: true,
                    material: ev,
                    pst: position_bonus,
                    value,
                });

                if piece.color == Color::Red {
                    hidden_value_red += value;
                } else {
                    hidden_value_black += value;
                }
            } else if let Some(pt) = piece.actual_type {
                // 明子：实际价值 + PST
                let pst_score = get_pst_score(
                    pt,
                    pos.row as usize,
                    pos.col as usize,
                    piece.color == Color::Red,
                ) as f64;
                let material = pt.value() as f64;
                let value = material + pst_score;

                let type_name = match pt {
                    PieceType::King => "King",
                    PieceType::Advisor => "Advisor",
                    PieceType::Elephant => "Elephant",
                    PieceType::Horse => "Horse",
                    PieceType::Rook => "Rook",
                    PieceType::Cannon => "Cannon",
                    PieceType::Pawn => "Pawn",
                };

                pieces.push(PieceEval {
                    position: pos_str,
                    color: color_str.to_string(),
                    piece_type: type_name.to_string(),
                    is_hidden: false,
                    material,
                    pst: pst_score,
                    value,
                });

                if piece.color == Color::Red {
                    material_red += material;
                    pst_red += pst_score;
                } else {
                    material_black += material;
                    pst_black += pst_score;
                }
            }
        }

        // 吃子潜力
        let capture_weight = 0.3;
        let red_capture = self.best_capture_value(board, Color::Red, black_hidden_ev);
        let black_capture = self.best_capture_value(board, Color::Black, red_hidden_ev);

        // 计算 raw_score（红方视角）
        let raw_score = (material_red - material_black)
            + (pst_red - pst_black)
            + (hidden_value_red - hidden_value_black)
            + capture_weight * (red_capture - black_capture);

        // 根据视角翻转符号
        let total = if color == Color::Red {
            raw_score
        } else {
            -raw_score
        };

        EvalDetail {
            pieces,
            material_red,
            material_black,
            pst_red,
            pst_black,
            hidden_ev_red: hidden_value_red,
            hidden_ev_black: hidden_value_black,
            capture_red: red_capture * capture_weight,
            capture_black: black_capture * capture_weight,
            total,
            pov: if color == Color::Red {
                "red".to_string()
            } else {
                "black".to_string()
            },
        }
    }

    /// 评估函数（从 color 视角）
    ///
    /// 内部逻辑：总是计算"红方价值 - 黑方价值"，最后根据视角翻转符号
    /// 这样避免 my/opp 的混淆，所有变量都是 red/black
    fn evaluate(&self, board: &Board, color: Color) -> f64 {
        // 按颜色固定计算暗子期望（不依赖 color 参数）
        let red_hidden_ev =
            HiddenPieceDistribution::from_board(board, Color::Red).expected_value() as f64;
        let black_hidden_ev =
            HiddenPieceDistribution::from_board(board, Color::Black).expected_value() as f64;

        // 内部总是计算：红方价值 - 黑方价值
        let mut raw_score = 0.0;

        for piece in board.get_all_pieces(None) {
            let (value, pst) = if piece.is_hidden {
                // 暗子：期望值 + 位置加成
                let ev = if piece.color == Color::Red {
                    red_hidden_ev
                } else {
                    black_hidden_ev
                };
                // 根据 movement_type（位置类型）和具体位置获取位置加成
                let position_bonus = piece
                    .movement_type
                    .map(|mt| hidden_position_bonus(mt, piece.position.col) as f64)
                    .unwrap_or(0.0);
                (ev + position_bonus, 0.0)
            } else if let Some(pt) = piece.actual_type {
                // 明子：实际价值 + PST
                let pos = piece.position;
                let pst_score = get_pst_score(
                    pt,
                    pos.row as usize,
                    pos.col as usize,
                    piece.color == Color::Red,
                ) as f64;
                (pt.value() as f64, pst_score)
            } else {
                (0.0, 0.0)
            };

            // 总是：红方加分，黑方减分
            if piece.color == Color::Red {
                raw_score += value + pst;
            } else {
                raw_score -= value + pst;
            }
        }

        // 吃子潜力（capture gain）
        // 红方吃黑方的子 → 被吃的暗子用 black_hidden_ev
        // 黑方吃红方的子 → 被吃的暗子用 red_hidden_ev
        let capture_weight = 0.3;
        let red_capture = self.best_capture_value(board, Color::Red, black_hidden_ev);
        let black_capture = self.best_capture_value(board, Color::Black, red_hidden_ev);
        raw_score += capture_weight * (red_capture - black_capture);

        // 最后根据视角翻转符号
        if color == Color::Red {
            raw_score
        } else {
            -raw_score
        }
    }

    /// 计算某方最佳吃子价值
    /// - attacker: 进攻方（谁在吃子）
    /// - victim_hidden_ev: 被吃方暗子的期望价值（attacker 吃的是对方的子）
    fn best_capture_value(&self, board: &Board, attacker: Color, victim_hidden_ev: f64) -> f64 {
        let moves = board.get_legal_moves(attacker);
        let mut best_gain: f64 = 0.0;

        for mv in &moves {
            if let Some(victim) = board.get_piece(mv.to_pos) {
                // 被吃子的价值
                let victim_value = if victim.is_hidden {
                    victim_hidden_ev
                } else {
                    victim.actual_type.map_or(0.0, |pt| pt.value() as f64)
                };

                // 排除吃 King（吃 King = 游戏结束，不应计入吃子潜力）
                if victim.actual_type == Some(PieceType::King) {
                    continue;
                }

                if victim_value > best_gain {
                    best_gain = victim_value;
                }
            }
        }

        best_gain
    }

    /// 终局评估
    /// ply: 从根节点开始的步数（半回合数），用于 Mate Distance Bonus
    fn terminal_eval(&self, board: &Board, color: Color, ply: i32) -> f64 {
        let result = board.get_game_result(None);
        let ply_bonus = (ply * PLY_PENALTY) as f64;

        match result {
            GameResult::RedWin => {
                if color == Color::Red {
                    // 赢得越快分数越高（ply 小 → 扣分少 → 分数高）
                    MATE_SCORE - ply_bonus
                } else {
                    // 输得越慢分数越高（负数越接近 0）
                    -MATE_SCORE + ply_bonus
                }
            }
            GameResult::BlackWin => {
                if color == Color::Black {
                    MATE_SCORE - ply_bonus
                } else {
                    -MATE_SCORE + ply_bonus
                }
            }
            GameResult::Draw => 0.0,
            GameResult::Ongoing => self.evaluate(board, color),
        }
    }

    /// Expectimax 搜索（Minimax 风格，固定 POV）
    fn expectimax(&self, board: &mut Board, ctx: SearchContext) -> f64 {
        // 节点计数
        NODE_COUNT.fetch_add(1, AtomicOrdering::Relaxed);

        // 超时检查：立即返回当前评估
        if self.is_timeout() {
            return self.evaluate(board, ctx.pov_color);
        }

        let current_color = board.current_turn();
        let legal_moves = board.get_legal_moves(current_color);
        let is_max_node = current_color == ctx.pov_color;

        // 终止条件：用 pov_color 评估
        if ctx.depth <= 0 || legal_moves.is_empty() {
            return self.terminal_eval(board, ctx.pov_color, ctx.ply);
        }

        if is_max_node {
            // MAX 节点：取最大值
            let mut max_eval = f64::NEG_INFINITY;
            for mv in &legal_moves {
                let eval = if mv.action_type == ActionType::RevealAndMove {
                    self.chance_node(board, mv, ctx, current_color)
                } else {
                    self.apply_move_and_recurse(board, mv, ctx)
                };
                max_eval = max_eval.max(eval);
                if max_eval >= ctx.beta {
                    break; // Beta 剪枝
                }
            }
            max_eval
        } else {
            // MIN 节点：取最小值
            let mut min_eval = f64::INFINITY;
            for mv in &legal_moves {
                let eval = if mv.action_type == ActionType::RevealAndMove {
                    self.chance_node(board, mv, ctx, current_color)
                } else {
                    self.apply_move_and_recurse(board, mv, ctx)
                };
                min_eval = min_eval.min(eval);
                if min_eval <= ctx.alpha {
                    break; // Alpha 剪枝
                }
            }
            min_eval
        }
    }

    /// Chance 节点：处理揭子走法的概率
    fn chance_node(
        &self,
        board: &mut Board,
        mv: &JieqiMove,
        ctx: SearchContext,
        color: Color,
    ) -> f64 {
        // 计算揭子方的剩余暗子分布
        let distribution = HiddenPieceDistribution::from_board(board, color);
        let possible_types = distribution.possible_types();

        if possible_types.is_empty() {
            // 理论上不应该发生，作为 fallback 直接递归
            return self.apply_move_and_recurse(board, mv, ctx);
        }

        let mut expected_value = 0.0;
        let next_ctx = ctx.next_ply();

        for (piece_type, probability) in possible_types {
            // 1. 模拟揭成该类型
            let reveal_state = board.simulate_reveal(mv.from_pos, piece_type);

            // 2. 执行走棋
            // 关键修复：构造一个 ActionType::Move 的走法，欺骗 Board 直接走棋
            // 否则 Board::make_move 会看到 RevealAndMove 强制把棋子类型改成位置类型
            let mut virtual_move = *mv;
            virtual_move.action_type = ActionType::Move;

            let was_hidden = reveal_state.is_some();
            let captured = board.make_move(&virtual_move);

            // 3. 递归搜索（固定 POV，不翻转）
            let child_value = self.expectimax(board, next_ctx);

            // 4. 撤销走棋
            board.undo_move(&virtual_move, captured, was_hidden);

            // 5. 恢复揭子模拟
            if let Some(state) = reveal_state {
                board.restore_simulated_reveal(mv.from_pos, state);
            }

            // 6. 累加期望值
            expected_value += probability * child_value;
        }

        expected_value
    }

    /// 普通走法的应用和递归
    fn apply_move_and_recurse(&self, board: &mut Board, mv: &JieqiMove, ctx: SearchContext) -> f64 {
        let was_hidden = board.get_piece(mv.from_pos).map_or(false, |p| p.is_hidden);
        let captured = board.make_move(mv);

        // next_ply: depth-1, ply+1（固定 POV，不翻转）
        let value = self.expectimax(board, ctx.next_ply());

        board.undo_move(mv, captured, was_hidden);

        value
    }

    /// 迭代加深搜索
    fn iterative_deepening(&self, board: &Board) -> Vec<(JieqiMove, f64)> {
        let moves = board.get_legal_moves(board.current_turn());
        if moves.is_empty() {
            return Vec::new();
        }

        let mut best_moves: Vec<(JieqiMove, f64)> = moves.iter().map(|&mv| (mv, 0.0)).collect();
        let start_time = Instant::now();
        // 设置开始时间，供内部超时检查使用
        self.start_time.set(Some(start_time));

        // 从深度 1 开始迭代
        for depth in 1..=self.max_depth {
            // 检查时间限制
            if let Some(limit) = self.time_limit {
                if start_time.elapsed() >= limit {
                    break;
                }
            }

            // 记录达到的深度
            DEPTH_REACHED.store(depth, AtomicOrdering::Relaxed);

            let mut current_scores: Vec<(JieqiMove, f64)> = Vec::new();

            for &mv in &moves {
                // 每个走法也检查时间限制
                if let Some(limit) = self.time_limit {
                    if start_time.elapsed() >= limit {
                        break;
                    }
                }

                let mut board_copy = board.clone();
                let pov_color = board.current_turn();

                // 揭子走法使用 Chance 节点
                let root_ctx = SearchContext::new(depth as i32, pov_color);
                let score = if mv.action_type == ActionType::RevealAndMove {
                    self.chance_node(&mut board_copy, &mv, root_ctx, pov_color)
                } else {
                    board_copy.make_move(&mv);
                    // 走了一步后进入下一层（固定 POV，不翻转）
                    self.expectimax(&mut board_copy, root_ctx.next_ply())
                };

                current_scores.push((mv, score));
            }

            // 只有完成整个深度的搜索才更新 best_moves
            if current_scores.len() == moves.len() {
                // 按分数排序
                current_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(CmpOrdering::Equal));
                best_moves = current_scores;
            }
        }

        best_moves
    }
}

impl AIStrategy for IT3AI {
    fn select_moves(&self, board: &Board, n: usize) -> Vec<ScoredMove> {
        let mut rng = self.rng.clone();
        let results = self.iterative_deepening(board);

        let mut scored: Vec<ScoredMove> = results
            .into_iter()
            .map(|(mv, score)| {
                let noise = if self.randomness > 0.0 {
                    rng.gen::<f64>() * self.randomness * 100.0
                } else {
                    0.0
                };
                ScoredMove {
                    mv,
                    score: score + noise,
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
    use crate::types::Position;

    #[test]
    fn test_hidden_piece_distribution() {
        // 揭棋初始局面：将帅已揭，其他暗子
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
        let board = Board::from_fen(fen).unwrap();

        let dist = HiddenPieceDistribution::from_board(&board, Color::Red);
        assert_eq!(dist.total_count(), 15); // 15 个暗子（将已揭）

        let possible = dist.possible_types();
        assert_eq!(possible.len(), 6); // 6 种可能（不含将）

        // 验证概率
        let total_prob: f64 = possible.iter().map(|(_, p)| p).sum();
        assert!((total_prob - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_expected_value() {
        // 揭棋初始局面
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXKXXXX -:- r r";
        let board = Board::from_fen(fen).unwrap();

        let dist = HiddenPieceDistribution::from_board(&board, Color::Red);
        let ev = dist.expected_value();

        // 期望价值（所有子力打8折）
        // Advisor: 2*160 + Elephant: 2*160 + Horse: 2*320 + Rook: 2*720 + Cannon: 2*360 + Pawn: 5*80
        // = 320 + 320 + 640 + 1440 + 720 + 400 = 3840
        // 3840 / 15 = 256
        assert_eq!(ev, 256);
    }

    #[test]
    fn test_it2_basic() {
        let fen = "4k4/9/9/9/4c4/4R4/9/9/9/4K4 -:- r r";
        let config = AIConfig {
            depth: 2,
            ..Default::default()
        };
        let ai = IT3AI::new(&config);
        let board = Board::from_fen(fen).unwrap();
        let moves = ai.select_moves(&board, 5);

        assert!(!moves.is_empty());
        // 最佳走法应该是吃炮
        assert_eq!(moves[0].mv.to_fen_str(None), "e4e5");
    }

    #[test]
    fn test_reveal_logic_fix() {
        // 构造一个局面：红方在 a0 (车位) 有一个暗子
        // 我们想验证：当 simulate_reveal 把它设为兵时，make_move 是否把它当兵走（而不是变回家车）
        let fen = "xxxxkxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/X8XXXX -:- r r"; // a0 is X
        let mut board = Board::from_fen(fen).unwrap();

        let from_pos = Position::new(0, 0); // a0
        let to_pos = Position::new(3, 0); // a3 (如果是车能走到，如果是兵走不到)

        // 我们手动模拟 chance_node 的逻辑
        let mv = JieqiMove {
            action_type: ActionType::RevealAndMove,
            from_pos,
            to_pos,
        };

        // 1. 模拟这个暗子是兵 (Pawn)
        // 兵在 a0 只能走到 1,0 (a1)
        let reveal_state = board.simulate_reveal(from_pos, PieceType::Pawn);
        assert!(reveal_state.is_some());

        // 2. 尝试用 ActionType::Move 走棋
        // 如果我们用原来的 ActionType::RevealAndMove，Board 会把它变成车
        let mut virtual_move = mv;
        virtual_move.action_type = ActionType::Move;

        // 兵在 a0 只能走一格，走不到 a3。make_move 不做合法性检查，只负责搬运。
        // 但我们需要验证搬运后的棋子类型是兵还是车。
        board.make_move(&virtual_move);

        let moved_piece = board.get_piece(to_pos).unwrap();
        // 修复前：它会变成 Rook (因为 a0 是车位)
        // 修复后：它应该保持 Pawn (因为我们 simulate_reveal 设置了 Pawn)
        assert_eq!(moved_piece.actual_type, Some(PieceType::Pawn));
        assert!(!moved_piece.is_hidden);
    }
}
