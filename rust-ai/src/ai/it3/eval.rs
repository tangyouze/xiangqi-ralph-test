//! IT2 评估模块 - 常量、PST、暗子分布、评估结构体

use crate::board::Board;
use crate::types::{Color, PieceType};

// === 常量定义 ===

/// 棋子类型数量
pub(super) const PIECE_TYPE_COUNT: usize = 7;

/// 初始棋子数量：King, Advisor, Elephant, Horse, Rook, Cannon, Pawn
pub(super) const INITIAL_COUNT: [u8; PIECE_TYPE_COUNT] = [1, 2, 2, 2, 2, 2, 5];

/// 棋子价值
pub(super) const PIECE_VALUES: [i32; PIECE_TYPE_COUNT] = [100000, 200, 200, 400, 900, 450, 100];

/// Mate score (胜负分)
pub(super) const MATE_SCORE: f64 = 100000.0;

/// Ply penalty multiplier for Mate Distance Bonus
/// 乘以 10 让不同步数的胜负分数差距更明显
pub(super) const PLY_PENALTY: i32 = 10;

/// 所有棋子类型
pub(super) const ALL_PIECE_TYPES: [PieceType; PIECE_TYPE_COUNT] = [
    PieceType::King,
    PieceType::Advisor,
    PieceType::Elephant,
    PieceType::Horse,
    PieceType::Rook,
    PieceType::Cannon,
    PieceType::Pawn,
];

/// 棋子类型转索引
#[inline]
pub(super) fn piece_type_to_index(pt: PieceType) -> usize {
    match pt {
        PieceType::King => 0,
        PieceType::Advisor => 1,
        PieceType::Elephant => 2,
        PieceType::Horse => 3,
        PieceType::Rook => 4,
        PieceType::Cannon => 5,
        PieceType::Pawn => 6,
    }
}

/// 暗子位置加成：根据 movement_type（位置类型）和具体位置给予不同的保护分
/// 鼓励揭开低价值位置的暗子，保护车位和炮位
pub(super) fn hidden_position_bonus(movement_type: PieceType, col: i8) -> i32 {
    match movement_type {
        PieceType::King => 0,
        PieceType::Advisor => -10,  // 士位
        PieceType::Elephant => -30, // 象位
        PieceType::Horse => -30,    // 马位
        PieceType::Rook => 50,      // 车位
        PieceType::Cannon => 20,    // 炮位
        PieceType::Pawn => {
            // 兵位：中间三个兵 (c/e/g列) vs 边上两个兵 (a/i列)
            if col == 0i8 || col == 8i8 {
                -30 // 边兵 (a/i, col=0,8)
            } else {
                -50 // 中间兵 (c/e/g, col=2,4,6)
            }
        }
    }
}

// === PST 表 ===

/// PST (Piece-Square Table) - 从红方视角，row 0 是红方底线
/// 每格分数单位：兵=100 时，PST 分数约 0-30
type PstTable = [[i32; 9]; 10];

/// 将/帅：待在九宫，中心稍好
const PST_KING: PstTable = [
    [0, 0, 0, 5, 10, 5, 0, 0, 0],
    [0, 0, 0, 5, 10, 5, 0, 0, 0],
    [0, 0, 0, 5, 5, 5, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
];

/// 士/仕：揭棋中可去任何位置，前进有加分
const PST_ADVISOR: PstTable = [
    [0, 0, 0, 5, 0, 5, 0, 0, 0],        // row 0: 底线
    [0, 0, 0, 0, 5, 0, 0, 0, 0],        // row 1
    [0, 0, 0, 5, 0, 5, 0, 0, 0],        // row 2
    [0, 0, 5, 5, 5, 5, 5, 0, 0],        // row 3: 出九宫
    [0, 5, 5, 10, 10, 10, 5, 5, 0],     // row 4: 河界
    [5, 5, 10, 10, 15, 10, 10, 5, 5],   // row 5: 过河
    [5, 10, 10, 15, 15, 15, 10, 10, 5], // row 6
    [5, 10, 15, 15, 20, 15, 15, 10, 5], // row 7
    [5, 10, 15, 20, 20, 20, 15, 10, 5], // row 8
    [0, 5, 10, 15, 25, 15, 10, 5, 0],   // row 9: 对方底线
];

/// 象/相：揭棋中可去任何位置，前进有加分
const PST_ELEPHANT: PstTable = [
    [0, 0, 5, 0, 0, 0, 5, 0, 0],        // row 0
    [0, 0, 0, 0, 0, 0, 0, 0, 0],        // row 1
    [5, 0, 0, 0, 10, 0, 0, 0, 5],       // row 2
    [0, 0, 0, 0, 0, 0, 0, 0, 0],        // row 3
    [0, 0, 5, 0, 0, 0, 5, 0, 0],        // row 4: 河界
    [5, 5, 10, 10, 15, 10, 10, 5, 5],   // row 5: 过河
    [5, 10, 10, 15, 15, 15, 10, 10, 5], // row 6
    [5, 10, 15, 15, 20, 15, 15, 10, 5], // row 7
    [5, 10, 15, 20, 20, 20, 15, 10, 5], // row 8
    [0, 5, 10, 15, 25, 15, 10, 5, 0],   // row 9: 对方底线
];

/// 马：中心和前方价值高
const PST_HORSE: PstTable = [
    [0, 0, 5, 10, 10, 10, 5, 0, 0],
    [0, 5, 10, 15, 15, 15, 10, 5, 0],
    [5, 10, 15, 20, 20, 20, 15, 10, 5],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [10, 15, 20, 25, 30, 25, 20, 15, 10],
    [10, 15, 20, 25, 30, 25, 20, 15, 10],
    [5, 10, 15, 20, 25, 20, 15, 10, 5],
    [0, 5, 10, 15, 20, 15, 10, 5, 0],
];

/// 车：开放线、前方价值高
const PST_ROOK: PstTable = [
    [10, 10, 10, 15, 15, 15, 10, 10, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [20, 25, 25, 30, 30, 30, 25, 25, 20],
    [20, 25, 25, 30, 30, 30, 25, 25, 20],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
];

/// 炮：中间位置价值高
const PST_CANNON: PstTable = [
    [10, 10, 10, 15, 15, 15, 10, 10, 10],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [15, 20, 20, 25, 25, 25, 20, 20, 15],
    [10, 15, 15, 20, 20, 20, 15, 15, 10],
    [5, 10, 10, 15, 15, 15, 10, 10, 5],
];

/// 兵/卒：过河后价值大增，越前越好
const PST_PAWN: PstTable = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [5, 0, 10, 0, 15, 0, 10, 0, 5],
    [10, 0, 15, 0, 20, 0, 15, 0, 10],
    [15, 20, 25, 30, 35, 30, 25, 20, 15],
    [20, 25, 30, 35, 40, 35, 30, 25, 20],
    [25, 30, 35, 40, 45, 40, 35, 30, 25],
    [30, 35, 40, 45, 50, 45, 40, 35, 30],
    [15, 20, 25, 30, 30, 30, 25, 20, 15], // row 9: 老兵威力减弱
];

/// 获取 PST 分数
#[inline]
pub(super) fn get_pst_score(piece_type: PieceType, row: usize, col: usize, is_red: bool) -> i32 {
    // 黑方需要翻转棋盘（row 9 变 row 0）
    let r = if is_red { row } else { 9 - row };

    match piece_type {
        PieceType::King => PST_KING[r][col],
        PieceType::Advisor => PST_ADVISOR[r][col],
        PieceType::Elephant => PST_ELEPHANT[r][col],
        PieceType::Horse => PST_HORSE[r][col],
        PieceType::Rook => PST_ROOK[r][col],
        PieceType::Cannon => PST_CANNON[r][col],
        PieceType::Pawn => PST_PAWN[r][col],
    }
}

// === 暗子分布 ===

/// 剩余暗子池的概率分布
#[derive(Debug, Clone)]
pub struct HiddenPieceDistribution {
    /// 每种棋子类型剩余数量
    remaining: [u8; PIECE_TYPE_COUNT],
    /// 剩余暗子总数
    total: u8,
}

impl HiddenPieceDistribution {
    /// 从棋盘状态计算某方的剩余暗子分布
    ///
    /// 使用 Board 中存储的 captured 信息来准确计算剩余暗子池。
    /// remaining = initial - revealed - captured
    pub fn from_board(board: &Board, color: Color) -> Self {
        let mut revealed: [u8; PIECE_TYPE_COUNT] = [0; PIECE_TYPE_COUNT];
        let mut hidden_count: u8 = 0;

        for piece in board.get_all_pieces(Some(color)) {
            if piece.is_hidden {
                hidden_count += 1;
            } else if let Some(pt) = piece.actual_type {
                let idx = piece_type_to_index(pt);
                revealed[idx] += 1;
            }
        }

        // 获取被吃子信息
        let (captured, captured_hidden) = board.get_captured(color);

        // 计算剩余暗子池：初始数量 - 已揭开 - 已被吃（明子）
        let mut remaining = [0u8; PIECE_TYPE_COUNT];
        for i in 0..PIECE_TYPE_COUNT {
            remaining[i] = INITIAL_COUNT[i]
                .saturating_sub(revealed[i])
                .saturating_sub(captured[i]);
        }

        // 处理被吃的暗子（类型未知）
        // 被吃的暗子需要从 remaining 中按比例扣除
        let sum_remaining: u8 = remaining.iter().sum();
        let effective_hidden = hidden_count; // 棋盘上的暗子数

        if captured_hidden > 0 && sum_remaining > effective_hidden {
            // 有暗子被吃了，需要从 remaining 中扣除
            // 按比例缩减 remaining 来匹配棋盘上的实际暗子数
            let target_total = effective_hidden.min(sum_remaining);
            if target_total > 0 && sum_remaining > target_total {
                let scale = target_total as f64 / sum_remaining as f64;
                let mut new_remaining = [0u8; PIECE_TYPE_COUNT];
                let mut total_assigned: u8 = 0;

                // 先按比例分配（向下取整）
                for i in 0..PIECE_TYPE_COUNT {
                    new_remaining[i] = (remaining[i] as f64 * scale).floor() as u8;
                    total_assigned += new_remaining[i];
                }

                // 分配剩余的（优先分配给高价值棋子）
                // 按价值降序：Rook(4), Cannon(5), Horse(3), Elephant(2), Advisor(1), Pawn(6)
                let priority_order = [4, 5, 3, 2, 1, 6]; // 跳过 King(0)
                let mut to_assign = target_total.saturating_sub(total_assigned);
                for &idx in &priority_order {
                    if to_assign == 0 {
                        break;
                    }
                    let can_add = remaining[idx].saturating_sub(new_remaining[idx]);
                    let add = can_add.min(to_assign);
                    new_remaining[idx] += add;
                    to_assign -= add;
                }

                remaining = new_remaining;
            }
        }

        HiddenPieceDistribution {
            remaining,
            total: hidden_count,
        }
    }

    /// 返回所有可能的棋子类型及其概率（过滤掉概率为0的）
    pub fn possible_types(&self) -> Vec<(PieceType, f64)> {
        if self.total == 0 {
            return Vec::new();
        }

        let total_remaining: u8 = self.remaining.iter().sum();
        if total_remaining == 0 {
            return Vec::new();
        }

        ALL_PIECE_TYPES
            .iter()
            .enumerate()
            .filter_map(|(i, &pt)| {
                if self.remaining[i] > 0 {
                    Some((pt, self.remaining[i] as f64 / total_remaining as f64))
                } else {
                    None
                }
            })
            .collect()
    }

    /// 计算期望价值（暗子所有子力打8折）
    pub fn expected_value(&self) -> i32 {
        let total_remaining: u8 = self.remaining.iter().sum();
        if total_remaining == 0 {
            return 300; // 默认值
        }

        let mut sum: i64 = 0;
        for i in 0..PIECE_TYPE_COUNT {
            // 暗子所有子力打8折
            let discounted_value = PIECE_VALUES[i] as i64 * 8 / 10;
            sum += (self.remaining[i] as i64) * discounted_value;
        }

        (sum / total_remaining as i64) as i32
    }

    /// 返回暗子池详细构成
    /// 返回 Vec<(类型名, 剩余数量, 单价, 总价)>
    #[allow(dead_code)]
    pub fn breakdown(&self) -> Vec<(String, u8, i32, i32)> {
        let type_names = [
            "King", "Advisor", "Elephant", "Horse", "Rook", "Cannon", "Pawn",
        ];
        let mut result = Vec::new();

        for i in 0..PIECE_TYPE_COUNT {
            if self.remaining[i] > 0 {
                // 暗子所有子力打8折
                let unit_value = PIECE_VALUES[i] * 8 / 10;
                let total_value = (self.remaining[i] as i32) * unit_value;
                result.push((
                    type_names[i].to_string(),
                    self.remaining[i],
                    unit_value,
                    total_value,
                ));
            }
        }
        result
    }

    /// 获取剩余暗子总数
    #[allow(dead_code)]
    pub fn total_count(&self) -> u8 {
        self.remaining.iter().sum()
    }
}

// === 评估结构体 ===

/// 单个棋子的评估详情
#[derive(Debug, Clone)]
pub struct PieceEval {
    /// 位置（如 "e0"）
    pub position: String,
    /// 颜色（red/black）
    pub color: String,
    /// 棋子类型（如 "Rook"、"hidden"）
    pub piece_type: String,
    /// 是否为暗子
    pub is_hidden: bool,
    /// 材料价值
    pub material: f64,
    /// 位置评分 (PST)
    pub pst: f64,
    /// 总价值（material + pst）
    pub value: f64,
}

/// 详细评估结果
#[derive(Debug, Clone, Default)]
pub struct EvalDetail {
    /// 所有棋子的详细评估
    pub pieces: Vec<PieceEval>,
    /// 红方材料价值
    pub material_red: f64,
    /// 黑方材料价值
    pub material_black: f64,
    /// 红方位置评分 (PST)
    pub pst_red: f64,
    /// 黑方位置评分 (PST)
    pub pst_black: f64,
    /// 红方暗子期望值
    pub hidden_ev_red: f64,
    /// 黑方暗子期望值
    pub hidden_ev_black: f64,
    /// 红方吃子潜力
    pub capture_red: f64,
    /// 黑方吃子潜力
    pub capture_black: f64,
    /// 总分（从指定视角）
    pub total: f64,
    /// 视角颜色
    pub pov: String,
}
