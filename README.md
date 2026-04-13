# Campus Assistant Bot

COMP7940 Cloud Computing Project, 2025/26 Semester 2.

A Telegram chatbot powered by DeepSeek LLM that helps university students with daily campus tasks. Built with Python, containerized with Docker, and deployed on the cloud.

## Architecture

```
User <-> Telegram <-> Bot (Python) <-> DeepSeek LLM API
                         |
                      Redis Cloud
                 (chat history, todos,
                  user profiles, logs)
```

## Features

**AI Chat** — Ask anything in natural language. The bot remembers conversation context.

**Task Management** — Add, complete, and delete tasks with optional deadlines. Data stored in Redis so nothing gets lost.

**Campus Events** — Browse and filter upcoming campus events by category (tech, sports, career, etc).

**Study Buddy Matching** — Set your interests and courses, then get matched with other users who share similar ones. Courses are weighted higher than interests in the matching score.

## Commands

```
/start              Start the bot
/help               Show all commands
/add <task>         Add a task (use | for deadline, e.g. /add Homework | 2026-04-20)
/list               View your tasks
/done <id>          Mark task complete
/deltask <id>       Delete a task
/events             Browse events (add category to filter, e.g. /events tech)
/profile <i> | <c>  Set interests and courses for matching
/myprofile          View your profile
/match              Find study buddies
/stats              Usage statistics
/health             System health check
/clear              Clear chat history
```

## Tech Stack

Python 3.11, python-telegram-bot, DeepSeek API (OpenAI-compatible), Redis Cloud, Docker, GitHub Actions for CI/CD.

## Setup

```bash
cp .env.example .env   # fill in your keys
pip install -r requirements.txt
python chatbot.py
```

Or with Docker:

```bash
docker build -t campus-bot .
docker run --env-file .env campus-bot
```

Or full stack with Docker Compose (includes local Redis and monitoring):

```bash
docker-compose up --build
```

## Environment Variables

See `.env.example` for the full list. You need a Telegram bot token, a DeepSeek API key, and Redis Cloud credentials.

## Cost

Everything runs on free tiers. Telegram API is free, Redis Cloud free tier gives 30MB, DeepSeek charges per token but costs are negligible for this scale. Total cost is effectively $0.
