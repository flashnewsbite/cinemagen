@echo off
title 📡 CinemaGen 24/7 Station (ON AIR)

:: 프로젝트 폴더로 이동 (회사 컴퓨터 경로에 맞게 확인 필수!)
:: 만약 회사 컴퓨터 경로가 다르다면 아래 경로를 수정해주세요.
cd /d "C:\Users\parkm\cinemagen"

:: 시작 메시지 출력
echo ========================================================
echo   CinemaGen Automation System is starting...
echo   Keep this window OPEN to stay ON AIR.
echo ========================================================

:: 스케줄러 실행
python scheduler.py

:: 혹시 에러가 나서 꺼지면 에러 메시지를 볼 수 있게 대기
pause