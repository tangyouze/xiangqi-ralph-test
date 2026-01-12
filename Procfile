backend: cd backend && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 6702 --reload
jieqi-backend: cd backend && source .venv/bin/activate && uvicorn jieqi_main:app --host 0.0.0.0 --port 6703 --reload
frontend: cd frontend && npm run dev -- --port 6701
ai-dashboard: cd backend && source .venv/bin/activate && streamlit run scripts/ai_dashboard.py --server.port 6704
