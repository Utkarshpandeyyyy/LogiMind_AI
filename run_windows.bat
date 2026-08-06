@echo off
echo ===================================================
echo   Starting LogiMind AI Platform & Infrastructure
echo ===================================================

echo.
echo [1/4] Starting Docker services (PostgreSQL, Kafka, Zookeeper)...
docker-compose up -d

echo.
echo [2/4] Verifying and installing Python dependencies...
python -m pip install -r requirements.txt

echo.
echo [3/4] Initializing and seeding the PostgreSQL Database...
python db_setup.py

echo.
echo [4/4] Launching the Supply Chain Decision Control Tower...
python -m streamlit run app.py
pause
