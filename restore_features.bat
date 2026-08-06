@echo off
echo.
echo ==========================================================
echo   Restoring LogiMind AI Features (RAG, Agents, Admin)...
echo ==========================================================
echo.

:: Reset tracked files to the commit containing all of your features
git reset --hard e8ee4c11e8f6377d86a2f60824ab3048f06b898d

:: Clean any untracked files
git clean -fd

echo.
echo ==========================================================
echo   Features successfully restored!
echo ==========================================================
pause
