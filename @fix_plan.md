# Xiangqi (Chinese Chess) Project Plan

## Completed

### Core Engine (Backend - Python)
- [x] Project structure and build system (pyproject.toml, uv)
- [x] Core types (Color, PieceType, Position, Move, GameResult)
- [x] Piece classes with move rules (King, Advisor, Elephant, Horse, Rook, Cannon, Pawn)
- [x] Board class (piece management, move validation, check detection)
- [x] Game class (turn management, move history, game state)
- [x] AI Engine with plugin architecture
- [x] RandomAI strategy
- [x] MinimaxAI with Alpha-Beta pruning
- [x] Position evaluator

### API Layer (FastAPI)
- [x] RESTful API endpoints
- [x] Game management (create, get, delete, list)
- [x] Move execution with validation
- [x] AI move requests
- [x] CORS support for frontend

### Frontend (React + TypeScript)
- [x] Board component with piece rendering
- [x] Game controls (mode selection, AI level)
- [x] Move interaction (select piece, show legal moves, make move)
- [x] Game status display
- [x] Support for Human vs Human, Human vs AI, AI vs AI modes

### Testing
- [x] Unit tests: 70 tests (types, pieces, board, game, AI)
- [x] Integration tests: 17 tests (API endpoints)
- [x] E2E tests: 8 tests (Playwright)
- [x] Code coverage: 91%

## Future Improvements

### High Priority
- [ ] WebSocket support for real-time updates
- [ ] Game persistence (save/load)
- [ ] Time controls

### Medium Priority
- [ ] Opening book for AI
- [ ] Endgame tablebases
- [ ] Position analysis features
- [ ] Move undo in UI

### Low Priority
- [ ] AI difficulty auto-adjustment
- [ ] Game replay feature
- [ ] Tournament mode
- [ ] Multi-language support

## Architecture Notes

```
backend/
├── xiangqi/
│   ├── types.py        # Core types (Color, Position, Move, etc.)
│   ├── piece.py        # Piece classes with move rules
│   ├── board.py        # Board state and validation
│   ├── game.py         # Game management
│   ├── ai/             # AI engine (pluggable strategies)
│   │   ├── base.py     # AIEngine and AIStrategy base
│   │   ├── random_ai.py
│   │   ├── minimax_ai.py
│   │   └── evaluator.py
│   └── api/            # FastAPI application
│       ├── app.py
│       ├── models.py
│       └── game_manager.py
└── tests/
    ├── unit/           # Unit tests
    └── integration/    # API tests

frontend/
├── src/
│   ├── components/     # React components
│   ├── api.ts          # API client
│   ├── types.ts        # TypeScript types
│   └── App.tsx         # Main application
└── e2e/                # Playwright E2E tests
```

## Running the Project

```bash
# Backend
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Tests
cd backend && pytest tests/
cd frontend && npm run test:e2e
```
