@echo off
setlocal
set DIR=%~dp0
set GRADLE_VERSION=8.7
set GRADLE_HOME=%DIR%.gradle\wrapper\dists\gradle-%GRADLE_VERSION%-bin\gradle-%GRADLE_VERSION%
if not exist "%GRADLE_HOME%in\gradle.bat" (
  echo Please install Gradle %GRADLE_VERSION% or run gradlew from Git Bash/WSL to auto-download it.
  exit /b 1
)
call "%GRADLE_HOME%in\gradle.bat" %*
