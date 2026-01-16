//! 揭棋测试局面库
//!
//! 提供命名的 FEN 测试局面，方便测试和调试
//!
//! 命名规范:
//! - START: 初始局面
//! - EARLY_n: 开局后1-5步
//! - MID_n: 中局 (10-30步)
//! - END_n: 残局
//! - CHECK_n: 将军测试
//! - MATE_n: 杀棋测试
//! - SPECIAL_n: 特殊情况测试

// =============================================================================
// 开局 (START)
// =============================================================================

/// 初始局面 - 所有棋子暗置，仅将帅明摆
pub const START: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/9/9/x1x1x1x1x/1x5x1/9/xxxxkxxxx -:- r r";

// =============================================================================
// 早期 (EARLY_1 ~ EARLY_20) - 开局后1-5步
// =============================================================================

/// 红方第一步: 中炮开局 (炮二平五)
pub const EARLY_1: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/9/4X4/x1x1x1x1x/1x5x1/9/xxxxkxxxx -:- b r";

/// 黑方回应: 进卒
pub const EARLY_2: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/4x4/4X4/x1x1x1x1x/1x5x1/9/xxxxkxxxx -:- r r";

/// 红方第二步: 马二进三
pub const EARLY_3: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/4x4/2X1X4/x1x1x1x1x/1x5x1/9/xxxxkxxxx -:- b r";

/// 黑方回应: 马8进7
pub const EARLY_4: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/4x4/2X1X4/x1x1x1x1x/9/1x5x1/xxxxkxxxx -:- r r";

/// 5步后的典型开局局面
pub const EARLY_5: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/4x4/2X1X1X2/x1x1x1x1x/9/1x3x1x1/xxxxkxxxx -:- b r";

/// 炮换马后的早期局面 (有明子)
pub const EARLY_6: &str = "XXXXKXXXX/9/1X5X1/X1X1C1X1X/4x4/2X5X/x1x1x1x1x/9/1x3x1x1/xxxxkxxxx C:h r r";

/// 双方都有明子的早期局面
pub const EARLY_7: &str = "XXXXKXXXX/9/1R5X1/X1X1C1X1X/4x4/2X5X/x1x1c1x1x/9/1r3x1x1/xxxxkxxxx C:h r r";

/// 中炮对屏风马
pub const EARLY_8: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/9/4X4/x1x1x1x1x/1x3x3/2x3x2/xxxxkxxxx -:- r r";

/// 仙人指路开局
pub const EARLY_9: &str = "XXXXKXXXX/9/1X5X1/X1X1X1X1X/9/2X6/x1x1x1x1x/1x5x1/9/xxxxkxxxx -:- b r";

/// 飞象开局
pub const EARLY_10: &str = "XXXXKXXXX/9/1X3X3/X1X1X1X1X/9/9/x1x1x1x1x/1x5x1/9/xxxxkxxxx -:- b r";

// 预留 EARLY_11 ~ EARLY_20
pub const EARLY_11: &str = START;
pub const EARLY_12: &str = START;
pub const EARLY_13: &str = START;
pub const EARLY_14: &str = START;
pub const EARLY_15: &str = START;
pub const EARLY_16: &str = START;
pub const EARLY_17: &str = START;
pub const EARLY_18: &str = START;
pub const EARLY_19: &str = START;
pub const EARLY_20: &str = START;

// =============================================================================
// 中期 (MID_1 ~ MID_30) - 大部分明子
// =============================================================================

/// 基础中局 - 双方各有一车明
pub const MID_1: &str = "4K4/9/4E4/R1P1P1P1R/9/9/r1p1p1p1r/4e4/9/4k4 -:- r r";

/// 车炮对攻
pub const MID_2: &str = "4K4/9/4E4/R1P1C1P1R/9/9/r1p1c1p1r/4e4/9/4k4 -:- r r";

/// 车马炮全的中局
pub const MID_3: &str = "1H2K2H1/9/4E4/R1P1C1P1R/9/9/r1p1c1p1r/4e4/9/1h2k2h1 -:- r r";

/// 有暗子的中局
pub const MID_4: &str = "1X2K2X1/9/4E4/R1X1C1X1R/9/9/r1x1c1x1r/4e4/9/1x2k2x1 -:- r r";

/// 红方优势的中局
pub const MID_5: &str = "4K4/9/4E4/R1P1C1P1R/4H4/9/r1p1p1p1r/4e4/9/4k4 -:- r r";

/// 黑方优势的中局
pub const MID_6: &str = "4K4/9/4E4/R1P1P1P1R/9/4h4/r1p1c1p1r/4e4/9/4k4 -:- r r";

/// 双车残局
pub const MID_7: &str = "4K4/9/9/R7R/9/9/r7r/9/9/4k4 -:- r r";

/// 车炮残局
pub const MID_8: &str = "4K4/9/9/R3C4/9/9/r3c4/9/9/4k4 -:- r r";

/// 车马残局
pub const MID_9: &str = "4K4/9/9/R3H4/9/9/r3h4/9/9/4k4 -:- r r";

/// 混合暗子中局
pub const MID_10: &str = "1XXXKxxx1/9/1X5x1/X1X1X1x1x/9/9/x1x1x1X1X/1x5X1/9/1xxxkXXX1 -:- r r";

// 预留 MID_11 ~ MID_30
pub const MID_11: &str = MID_1;
pub const MID_12: &str = MID_1;
pub const MID_13: &str = MID_1;
pub const MID_14: &str = MID_1;
pub const MID_15: &str = MID_1;
pub const MID_16: &str = MID_1;
pub const MID_17: &str = MID_1;
pub const MID_18: &str = MID_1;
pub const MID_19: &str = MID_1;
pub const MID_20: &str = MID_1;
pub const MID_21: &str = MID_1;
pub const MID_22: &str = MID_1;
pub const MID_23: &str = MID_1;
pub const MID_24: &str = MID_1;
pub const MID_25: &str = MID_1;
pub const MID_26: &str = MID_1;
pub const MID_27: &str = MID_1;
pub const MID_28: &str = MID_1;
pub const MID_29: &str = MID_1;
pub const MID_30: &str = MID_1;

// =============================================================================
// 残局 (END_1 ~ END_20) - 少量棋子
// =============================================================================

/// 单车残局
pub const END_1: &str = "4K4/9/9/9/4R4/9/9/9/9/4k4 -:- r r";

/// 单炮残局
pub const END_2: &str = "4K4/9/9/9/4C4/9/9/9/9/4k4 -:- r r";

/// 单马残局
pub const END_3: &str = "4K4/9/9/9/4H4/9/9/9/9/4k4 -:- r r";

/// 车兵残局
pub const END_4: &str = "4K4/9/9/4P4/4R4/9/9/9/9/4k4 -:- r r";

/// 双兵残局
pub const END_5: &str = "4K4/9/9/2P1P4/9/9/9/9/9/4k4 -:- r r";

/// 炮兵残局
pub const END_6: &str = "4K4/9/9/4P4/4C4/9/9/9/9/4k4 -:- r r";

/// 马兵残局
pub const END_7: &str = "4K4/9/9/4P4/4H4/9/9/9/9/4k4 -:- r r";

/// 车马残局 (红方)
pub const END_8: &str = "4K4/9/9/9/2R1H4/9/9/9/9/4k4 -:- r r";

/// 车炮残局 (红方)
pub const END_9: &str = "4K4/9/9/9/2R1C4/9/9/9/9/4k4 -:- r r";

/// 双方各有车
pub const END_10: &str = "4K4/9/9/9/4R4/9/4r4/9/9/4k4 -:- r r";

// 预留 END_11 ~ END_20
pub const END_11: &str = END_1;
pub const END_12: &str = END_1;
pub const END_13: &str = END_1;
pub const END_14: &str = END_1;
pub const END_15: &str = END_1;
pub const END_16: &str = END_1;
pub const END_17: &str = END_1;
pub const END_18: &str = END_1;
pub const END_19: &str = END_1;
pub const END_20: &str = END_1;

// =============================================================================
// 将军 (CHECK_1 ~ CHECK_10) - 将军局面测试
// =============================================================================

/// 车将军
pub const CHECK_1: &str = "4K4/9/9/9/9/9/9/9/4R4/4k4 -:- r r";

/// 炮将军 (需要炮架)
pub const CHECK_2: &str = "4K4/9/9/9/4P4/9/9/9/4C4/4k4 -:- r r";

/// 马将军
pub const CHECK_3: &str = "4K4/9/9/9/9/9/9/3H5/9/4k4 -:- r r";

/// 飞将 (将对将)
pub const CHECK_4: &str = "4K4/9/9/9/9/9/9/9/9/4k4 -:- r r";

/// 双将 (车+马)
pub const CHECK_5: &str = "4K4/9/9/9/9/9/9/3H5/4R4/4k4 -:- r r";

/// 暗子将军 (暗子在车位)
pub const CHECK_6: &str = "4K4/9/9/9/9/9/9/9/4X4/4k4 -:- r r";

/// 炮架是暗子的将军
pub const CHECK_7: &str = "4K4/9/9/9/4X4/9/9/9/4C4/4k4 -:- r r";

/// 侧面车将军
pub const CHECK_8: &str = "4K4/9/9/9/9/9/9/9/9/R3k4 -:- r r";

/// 底线炮将军
pub const CHECK_9: &str = "4K4/9/9/9/9/9/4P4/9/9/C3k4 -:- r r";

/// 卧槽马将军
pub const CHECK_10: &str = "4K4/9/9/9/9/9/9/5H3/9/4k4 -:- r r";

// =============================================================================
// 杀棋 (MATE_1 ~ MATE_10) - 可将死的局面
// =============================================================================

/// 1步杀 - 白脸将
pub const MATE_1: &str = "4K4/9/9/9/9/9/9/9/9/4k4 -:- r r";

/// 1步杀 - 车杀
pub const MATE_2: &str = "3AKA3/9/9/9/9/9/9/9/4R4/4k4 -:- r r";

/// 1步杀 - 双车错
pub const MATE_3: &str = "4K4/9/9/9/9/9/9/9/R3R4/4k4 -:- r r";

/// 2步杀 - 铁门栓
pub const MATE_4: &str = "4K4/9/9/9/9/9/4P4/9/4C4/3Ak4 -:- r r";

/// 2步杀 - 闷宫
pub const MATE_5: &str = "4K4/9/9/9/9/9/9/9/4H4/3AkA3 -:- r r";

/// 3步杀 - 海底捞月
pub const MATE_6: &str = "4K4/9/9/9/4R4/9/9/9/9/4k4 -:- r r";

/// 杀局: 车炮配合
pub const MATE_7: &str = "4K4/9/9/9/4C4/9/9/9/4R4/4k4 -:- r r";

/// 杀局: 双车侧翼
pub const MATE_8: &str = "4K4/9/9/9/9/9/9/9/9/R2Ak3R -:- r r";

/// 杀局: 马后炮
pub const MATE_9: &str = "4K4/9/9/9/9/9/3H5/9/4C4/4k4 -:- r r";

/// 杀局: 挂角马
pub const MATE_10: &str = "4K4/9/9/9/9/9/9/3H5/4R4/3Ak4 -:- r r";

// =============================================================================
// 特殊 (SPECIAL_1 ~ SPECIAL_10) - 边界情况测试
// =============================================================================

/// 士过河测试 - 明士可以过河
pub const SPECIAL_1: &str = "4K4/9/9/4A4/9/9/9/9/9/4k4 -:- r r";

/// 象过河测试 - 明象可以过河
pub const SPECIAL_2: &str = "4K4/9/9/9/2E6/9/9/9/9/4k4 -:- r r";

/// 马蹩腿测试 - 马被蹩
pub const SPECIAL_3: &str = "4K4/9/9/9/3PH4/9/9/9/9/4k4 -:- r r";

/// 象眼测试 - 象眼被堵
pub const SPECIAL_4: &str = "4K4/9/9/4P4/2E6/9/9/9/9/4k4 -:- r r";

/// 炮架测试 - 多个炮架
pub const SPECIAL_5: &str = "4K4/9/9/4P4/4P4/9/4P4/9/4C4/4k4 -:- r r";

/// 暗子揭开测试 - 混合暗明
pub const SPECIAL_6: &str = "XXXXKXXXX/9/1R5X1/X1X1X1X1X/9/9/x1x1x1x1x/1x5r1/9/xxxxkxxxx -:- r r";

/// 边界位置测试 - 棋子在角落
pub const SPECIAL_7: &str = "R3K3R/9/9/9/9/9/9/9/9/r3k3r -:- r r";

/// 九宫测试 - 士在九宫内
pub const SPECIAL_8: &str = "3AKA3/9/9/9/9/9/9/9/9/3aka3 -:- r r";

/// 兵过河测试 - 兵可以横走
pub const SPECIAL_9: &str = "4K4/9/9/9/9/4P4/9/9/9/4k4 -:- r r";

/// 复杂暗子局面
pub const SPECIAL_10: &str = "XXXXKxxxx/9/1X5x1/X1X1x1X1x/9/9/x1x1X1x1X/1x5X1/9/xxxxkXXXX -:- r r";

// =============================================================================
// 位置集合 - 方便遍历测试
// =============================================================================

/// 所有早期局面
pub const EARLY_POSITIONS: [&str; 20] = [
    EARLY_1, EARLY_2, EARLY_3, EARLY_4, EARLY_5,
    EARLY_6, EARLY_7, EARLY_8, EARLY_9, EARLY_10,
    EARLY_11, EARLY_12, EARLY_13, EARLY_14, EARLY_15,
    EARLY_16, EARLY_17, EARLY_18, EARLY_19, EARLY_20,
];

/// 所有中期局面
pub const MID_POSITIONS: [&str; 30] = [
    MID_1, MID_2, MID_3, MID_4, MID_5,
    MID_6, MID_7, MID_8, MID_9, MID_10,
    MID_11, MID_12, MID_13, MID_14, MID_15,
    MID_16, MID_17, MID_18, MID_19, MID_20,
    MID_21, MID_22, MID_23, MID_24, MID_25,
    MID_26, MID_27, MID_28, MID_29, MID_30,
];

/// 所有残局局面
pub const END_POSITIONS: [&str; 20] = [
    END_1, END_2, END_3, END_4, END_5,
    END_6, END_7, END_8, END_9, END_10,
    END_11, END_12, END_13, END_14, END_15,
    END_16, END_17, END_18, END_19, END_20,
];

/// 所有将军测试局面
pub const CHECK_POSITIONS: [&str; 10] = [
    CHECK_1, CHECK_2, CHECK_3, CHECK_4, CHECK_5,
    CHECK_6, CHECK_7, CHECK_8, CHECK_9, CHECK_10,
];

/// 所有杀棋测试局面
pub const MATE_POSITIONS: [&str; 10] = [
    MATE_1, MATE_2, MATE_3, MATE_4, MATE_5,
    MATE_6, MATE_7, MATE_8, MATE_9, MATE_10,
];

/// 所有特殊测试局面
pub const SPECIAL_POSITIONS: [&str; 10] = [
    SPECIAL_1, SPECIAL_2, SPECIAL_3, SPECIAL_4, SPECIAL_5,
    SPECIAL_6, SPECIAL_7, SPECIAL_8, SPECIAL_9, SPECIAL_10,
];

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Board;

    #[test]
    fn test_start_position_valid() {
        let board = Board::from_fen(START);
        assert!(board.is_ok(), "START position invalid: {:?}", board.err());
    }

    #[test]
    fn test_all_early_positions_valid() {
        for (i, fen) in EARLY_POSITIONS.iter().enumerate() {
            let board = Board::from_fen(fen);
            assert!(board.is_ok(), "EARLY_{} invalid: {:?}", i + 1, board.err());
        }
    }

    #[test]
    fn test_all_mid_positions_valid() {
        for (i, fen) in MID_POSITIONS.iter().enumerate() {
            let board = Board::from_fen(fen);
            assert!(board.is_ok(), "MID_{} invalid: {:?}", i + 1, board.err());
        }
    }

    #[test]
    fn test_all_end_positions_valid() {
        for (i, fen) in END_POSITIONS.iter().enumerate() {
            let board = Board::from_fen(fen);
            assert!(board.is_ok(), "END_{} invalid: {:?}", i + 1, board.err());
        }
    }

    #[test]
    fn test_all_check_positions_valid() {
        for (i, fen) in CHECK_POSITIONS.iter().enumerate() {
            let board = Board::from_fen(fen);
            assert!(board.is_ok(), "CHECK_{} invalid: {:?}", i + 1, board.err());
        }
    }

    #[test]
    fn test_all_mate_positions_valid() {
        for (i, fen) in MATE_POSITIONS.iter().enumerate() {
            let board = Board::from_fen(fen);
            assert!(board.is_ok(), "MATE_{} invalid: {:?}", i + 1, board.err());
        }
    }

    #[test]
    fn test_all_special_positions_valid() {
        for (i, fen) in SPECIAL_POSITIONS.iter().enumerate() {
            let board = Board::from_fen(fen);
            assert!(board.is_ok(), "SPECIAL_{} invalid: {:?}", i + 1, board.err());
        }
    }
}
