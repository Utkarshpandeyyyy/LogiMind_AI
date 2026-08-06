@echo off
echo.
echo ===========================================
echo   Pushing 2:00 PM state to GitHub...
echo ===========================================
echo.

:: Force-push the current local state to the main branch on GitHub
git push -f origin main

echo.
echo ===========================================
echo   Push completed!
echo ===========================================
pause
