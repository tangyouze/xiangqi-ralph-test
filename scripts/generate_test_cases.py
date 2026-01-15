#!/usr/bin/env python3
"""
生成跨语言测试用例 - 简化版

直接使用预定义的FEN字符串生成测试用例
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0,str(Path(__file__).parent.parent))

from jieqi.board import JieqiBoard
from jieqi.fen import parse_fen
from jieqi.types import Color


def main():
    print("生成测试用例...\n")
    
    # 预定义的测试FEN (ID, FEN, 描述)
    test_fens = [
        # 开局
        ("opening_001", "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/1X5X1/9/XXXXXXXXX -:- r r", "opening"),
        
        # 特殊用例 - 炮隔2子
        ("special_001_cannon_2screens", "xxxxxxxxx/9/1x5x1/x1x1x1x1x/9/9/X1X1X1X1X/4C2X1/9/XXXXXXXXX -:- b r", "special"),
        
        # 特殊用例 - 炮隔1子将军
        ("special_002_cannon_1screen", "9/4k4/4P4/4C4/9/9/9/9/9/4K4 -:- b r", "special"),
        
        # 特殊用例 - 将帅对脸
        ("special_003_king_facing", "4k4/9/9/9/9/9/9/9/9/4K4 -:- r r", "special"),
        
        # 特殊用例 - 车将军
        ("special_004_rook_check", "4k4/4R4/9/9/9/9/9/9/9/4K4 -:- b r", "special"),
        
        # 对称局面
        ("special_005_symmetric", "4k4/9/9/9/4r4/4R4/9/9/9/4K4 -:- r r", "special"),
    ]
    
    all_cases = []
    
    for test_id, fen, source in test_fens:
        try:
            state = parse_fen(fen)
            board = JieqiBoard.from_fen(fen)
            
            current_color = state.turn
            moves = board.get_legal_moves(current_color)
            is_in_check = board.is_in_check(current_color)
            game_result = board.get_game_result(current_color)
            
            case = {
                "id": test_id,
               "fen": fen,
                "turn": "red" if current_color == Color.RED else "black",
                "expected_move_count": len(moves),
                "is_in_check": is_in_check,
                "game_result": game_result.value,
                "source": source
            }
            
            all_cases.append(case)
            print(f"✓ {test_id}: {len(moves)} 个走法")
            
        except Exception as e:
            print(f"✗ {test_id}: {e}")
    
    # 保存为JSON
    output_file = Path(__file__).parent.parent / "test_cases.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_cases, f, indent=2, ensure_ascii=False)
    
    print(f"\n总计: {len(all_cases)} 个测试用例")
    print(f"已保存到: {output_file}")


if __name__ == "__main__":
    main()
