# Locket Gold Activator Telegram Bot

## Overview
A Telegram bot for automating Locket Gold activation. Built with Python, python-telegram-bot, aiohttp, and SQLite.

## Project Architecture
- `main.py` - Entry point, runs the bot
- `app/bot.py` - Bot logic, handlers, queue workers
- `app/config.py` - Configuration, tokens, text translations
- `app/database.py` - SQLite database operations
- `app/services/locket.py` - Locket API integration
- `app/services/nextdns.py` - NextDNS profile management

## Environment Variables
- `BOT_TOKEN` (secret) - Telegram Bot API token from @BotFather
- `NEXTDNS_KEY` (secret) - NextDNS API key

## Running
- Workflow: `python main.py` (console mode)
- No frontend; this is a console-based Telegram bot

## Database
- SQLite (`bot_data.db`) - stores usage logs, user settings, bot config, request logs

## Dependencies
- python-telegram-bot
- aiohttp
- requests
