# Archived AI Strategies

This document contains algorithm ideas from deleted AI strategies.
These were experimental or intermediate versions that have been superseded.

## Kept Strategies (Active)

- **random** (v001) - Random baseline
- **greedy** (v002) - Simple material evaluation
- **minimax** (v011) - Basic minimax search
- **iterative** (v013) - Iterative deepening with time control
- **muses** (v016) - Main AI with PVS, TT, LMR, Quiescence
- **mcts** (v018) - Monte Carlo Tree Search

---

## Archived Strategies

### v003_positional - Position Evaluation

**Idea**: Add position-based evaluation on top of material.

Key concepts:
- Center positions are more valuable
- Crossed-river pieces get bonus
- Closer to enemy king = higher value
- Attacker/defender counting for safety

### v004_defensive - Defense Priority

**Idea**: Enhance defense, avoid losing pieces.

Key concepts:
- Stronger capture risk evaluation
- Protect high-value pieces
- Don't expose the king easily

### v005_aggressive - Offensive AI

**Idea**: Add offensive capability with 1-ply lookahead.

Key concepts:
- Threaten enemy high-value pieces (bonus)
- Get closer to enemy king (bonus)
- Control key positions
- 1-ply lookahead to avoid blunders

### v006_balanced - Balanced Attack/Defense

**Idea**: Combine defensive and positional strategies.

Key concepts:
- Defense-first (from v004)
- Position evaluation (from v003)
- Moderate offense
- Piece coordination

### v007_reveal - Smart Reveal Strategy

**Idea**: Optimize when and how to reveal hidden pieces.

Key concepts:
- Smart timing for reveals
- Evaluate position safety before reveal
- Consider threat capability after reveal
- Prefer revealing in protected positions
- More aggressive reveals in late game

### v008_lookahead - One-Step Lookahead

**Idea**: Predict opponent's best response.

Key concepts:
- Evaluate opponent's best reply after our move
- Consider opponent capture threats
- Avoid being recaptured

### v009_coordination - Piece Coordination

**Idea**: Evaluate piece cooperation.

Key concepts:
- Double rook coordination bonus
- Cannon + horse synergy
- Protection chain evaluation
- Mutual support capability

### v010_fast - Fast Evaluation

**Idea**: Performance-optimized evaluation.

Key concepts:
- Simplified evaluation logic
- Combine best ideas from v007
- Fast material calculation

### v012_alphabeta - Alpha-Beta with TT

**Idea**: Add transposition table to basic search.

Key concepts:
- Transposition Table (TT) caching
- Improved move ordering (captures, checks first)
- Killer move heuristic
- History heuristic

*Note: These concepts are now in muses (v016)*

### v014_advanced - Advanced Search

**Idea**: More evaluation factors and search optimizations.

Key concepts:
- Late Move Reduction (LMR)
- Principal Variation Search (PVS)
- Piece-square tables
- Piece coordination evaluation
- King safety
- Better move ordering

*Note: These concepts are now in muses (v016)*

### v015_master - Master AI

**Status**: Empty/incomplete implementation

### v017_muses2 - Improved Muses

**Idea**: Deep optimization of muses AI.

Key concepts:
- More aggressive Null Move Pruning
- Improved quiescence search (from miaosisrai)
- Rooted pieces detection
- Dynamic evaluation adjustment
- Hidden rook capture priority

### v019_mcts_rave - MCTS with RAVE

**Idea**: MCTS + Rapid Action Value Estimation.

Key concepts:
- RAVE shares move statistics to speed up learning
- AMAF (All Moves As First) for quick move estimates
- Dynamic balance between UCT and RAVE
- Good for learning strategies in Jieqi

### v020_mcts_eval - MCTS with Evaluation

**Idea**: MCTS + evaluation function hybrid (AlphaGo style).

Key concepts:
- Shallow playout + evaluation function (like Value Network)
- More iterations, deeper search
- Progressive Widening for high branching factor
- Supports longer time deep search

### v021_pvs - Advanced PVS

**Idea**: PVS with advanced pruning techniques.

Key concepts:
- Null Move Pruning (NMP)
- Aspiration Windows
- Futility Pruning
- Countermove Heuristic
- Late Move Pruning (LMP)
- Internal Iterative Deepening (IID)
- Static Exchange Evaluation (SEE)

*Note: Many of these are in muses (v016)*

---

## Rust Archived Strategies

The following Rust strategies were also removed:
- **positional** - Position evaluation (concepts in evaluator)
- **defensive** - Defense priority
- **aggressive** - Offensive play

---

## Future Ideas

If reviving any of these:
1. Start from muses (v016) as base
2. Add the specific concept you want to test
3. Benchmark against muses to verify improvement
