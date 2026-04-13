import logging
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import config
import db
import llm

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler so Render free tier sees a listening port."""

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! 👋\n\n"
        "I'm your *Campus Assistant Bot* powered by AI.\n\n"
        "🎓 *Features:*\n"
        "• Ask me anything in natural language\n"
        "• Manage your tasks & deadlines\n"
        "• Browse campus events\n"
        "• Find study buddies with shared interests\n\n"
        "📋 *Commands:*\n"
        "/help — Full command list\n"
        "/add — Add a task or deadline\n"
        "/list — View your tasks\n"
        "/events — Browse campus events\n"
        "/profile — Set your interests for matching\n"
        "/match — Find study buddies\n"
        "/stats — Bot usage statistics\n"
        "/health — System health check",
        parse_mode="Markdown",
    )
    logger.info("User %s (%s) started the bot", user.id, user.username)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 *Campus Assistant Bot — Help*\n\n"
        "*💬 AI Chat*\n"
        "Just type any message and I'll respond using AI!\n\n"
        "*📝 Task Management*\n"
        "`/add <task>` — Add a new task\n"
        "`/add <task> | <deadline>` — Add task with deadline\n"
        "`/list` — View all your tasks\n"
        "`/done <id>` — Mark a task as complete\n"
        "`/deltask <id>` — Delete a task\n\n"
        "*🎉 Campus Events*\n"
        "`/events` — Browse all events\n"
        "`/events <category>` — Filter by category\n\n"
        "*👥 Study Buddy*\n"
        "`/profile <interests> | <courses>` — Set your profile\n"
        "`/myprofile` — View your profile\n"
        "`/match` — Find study buddies\n\n"
        "*📊 System*\n"
        "`/stats` — Usage statistics\n"
        "`/health` — System health check\n"
        "`/clear` — Clear chat history",
        parse_mode="Markdown",
    )


# task management handlers
async def add_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Usage:\n"
            "`/add Buy textbook`\n"
            "`/add Submit COMP7940 report | 2026-04-14`",
            parse_mode="Markdown",
        )
        return

    parts = text.split("|", 1)
    task_text = parts[0].strip()
    deadline = parts[1].strip() if len(parts) > 1 else ""

    todo = db.add_todo(user.id, task_text, deadline)
    if todo:
        msg = f"✅ Task added! (ID: {todo['id']})\n📌 {task_text}"
        if deadline:
            msg += f"\n⏰ Deadline: {deadline}"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("❌ Failed to add task. Please try again.")


async def list_todos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    todos = db.get_todos(user.id)

    if not todos:
        await update.message.reply_text(
            "📭 No tasks yet! Use `/add` to create one.",
            parse_mode="Markdown",
        )
        return

    lines = ["📋 *Your Tasks:*\n"]
    for t in todos:
        status = "✅" if t.get("done") else "⬜"
        line = f"{status} *{t['id']}*. {t['text']}"
        if t.get("deadline"):
            line += f" (⏰ {t['deadline']})"
        lines.append(line)

    lines.append(f"\n_Total: {len(todos)} tasks_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def done_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: `/done <task_id>`", parse_mode="Markdown")
        return
    try:
        todo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid task ID number.")
        return

    if db.complete_todo(user.id, todo_id):
        await update.message.reply_text(f"✅ Task {todo_id} marked as complete!")
    else:
        await update.message.reply_text(f"❌ Task {todo_id} not found.")


async def del_todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: `/deltask <task_id>`", parse_mode="Markdown")
        return
    try:
        todo_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid task ID number.")
        return

    if db.delete_todo(user.id, todo_id):
        await update.message.reply_text(f"🗑️ Task {todo_id} deleted!")
    else:
        await update.message.reply_text(f"❌ Task {todo_id} not found.")


# campus events handler
async def events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category = " ".join(context.args).strip().lower() if context.args else ""
    event_list = db.get_events(category) if category else db.get_events()

    if not event_list:
        categories = ", ".join(db.get_event_categories())
        await update.message.reply_text(
            f"No events found for '{category}'.\n\n"
            f"Available categories: {categories}\n\n"
            "Use `/events <category>` to filter.",
            parse_mode="Markdown",
        )
        return

    lines = ["🎉 *Campus Events:*\n"]
    for e in event_list:
        lines.append(
            f"📅 *{e['title']}*\n"
            f"   Date: {e['date']} | 📍 {e['location']}\n"
            "   Category: #" + e['category'] + "\n"
        )

    if not category:
        categories = ", ".join(db.get_event_categories())
        lines.append("_Filter by category:_ `/events <category>`")
        lines.append(f"_Categories: {categories}_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# study buddy matching handlers
async def set_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = " ".join(context.args) if context.args else ""

    if not text:
        await update.message.reply_text(
            "Set your profile for study buddy matching!\n\n"
            "Usage:\n"
            "`/profile interests | courses`\n\n"
            "Example:\n"
            "`/profile AI, Python, Cloud | COMP7940, COMP7980`",
            parse_mode="Markdown",
        )
        return

    parts = text.split("|", 1)
    interests = [i.strip() for i in parts[0].split(",") if i.strip()]
    courses = [c.strip() for c in parts[1].split(",") if c.strip()] if len(parts) > 1 else []

    db.set_profile(user.id, user.username or user.first_name, interests, courses)

    await update.message.reply_text(
        "👤 *Profile Updated!*\n\n"
        f"🎯 Interests: {', '.join(interests)}\n"
        f"📚 Courses: {', '.join(courses) if courses else 'None set'}\n\n"
        "Use `/match` to find study buddies!",
        parse_mode="Markdown",
    )


async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    profile = db.get_profile(user.id)

    if not profile:
        await update.message.reply_text(
            "You haven't set up a profile yet.\nUse `/profile` to get started!",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        "👤 *Your Profile*\n\n"
        f"🎯 Interests: {', '.join(profile.get('interests', []))}\n"
        f"📚 Courses: {', '.join(profile.get('courses', []))}\n"
        f"📅 Updated: {profile.get('updated', 'N/A')[:10]}",
        parse_mode="Markdown",
    )


async def match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    profile = db.get_profile(user.id)

    if not profile:
        await update.message.reply_text(
            "Please set up your profile first with `/profile`!",
            parse_mode="Markdown",
        )
        return

    matches = db.find_matches(user.id)

    if not matches:
        await update.message.reply_text(
            "🔍 No matches found yet.\n"
            "More users need to register their profiles!\n"
            "Share this bot with your classmates 😊"
        )
        return

    lines = ["👥 *Study Buddy Matches:*\n"]
    for i, m in enumerate(matches, 1):
        lines.append(f"*{i}. @{m['username']}*")
        if m["common_courses"]:
            lines.append(f"   📚 Same courses: {', '.join(m['common_courses'])}")
        if m["common_interests"]:
            lines.append(f"   🎯 Same interests: {', '.join(m['common_interests'])}")
        lines.append(f"   ⭐ Match score: {m['score']}\n")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# system commands
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.clear_history(update.effective_user.id)
    await update.message.reply_text("✅ Conversation history cleared!")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = db.get_stats()
    logs = db.get_recent_logs(5)

    lines = [
        "📊 *Bot Statistics*\n",
        f"Total requests: {s['total_requests']}",
        f"Registered users: {s['registered_users']}",
    ]

    if logs:
        lines.append("\n📝 *Recent Activity:*")
        for log in logs[:5]:
            lines.append(
                f"• {log.get('username', 'N/A')}: "
                f"\"{log.get('message', '')[:30]}\" "
                f"({log.get('latency_ms', 0)}ms)"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    redis_ok = db.health_check()
    status = "✅ All systems operational" if redis_ok else "❌ Redis connection failed"
    await update.message.reply_text(
        "🏥 *Health Check*\n\n"
        f"• Redis: {'✅ Connected' if redis_ok else '❌ Disconnected'}\n"
        f"• LLM: ✅ {config.LLM_MODEL}\n"
        "• Bot: ✅ Running\n\n"
        f"Status: {status}",
        parse_mode="Markdown",
    )


# forward user messages to the LLM
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_message = update.message.text
    if not user_message:
        return

    logger.info("Message from %s (%s): %s", user.id, user.username, user_message[:100])
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    history = db.get_history(user.id)

    start_time = time.time()
    reply = llm.chat(history, user_message)
    latency_ms = int((time.time() - start_time) * 1000)

    db.save_message(user.id, "user", user_message)
    db.save_message(user.id, "assistant", reply)
    db.log_request(user.id, user.username or "", user_message, reply, latency_ms)

    logger.info("Reply to %s (latency=%dms): %s", user.id, latency_ms, reply[:100])

    # telegram has a 4096 char limit per message
    if len(reply) > 4096:
        for i in range(0, len(reply), 4096):
            await update.message.reply_text(reply[i:i + 4096])
    else:
        await update.message.reply_text(reply)


def main() -> None:
    if not config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set!")
        return
    if not config.LLM_API_KEY:
        logger.error("LLM_API_KEY is not set!")
        return

    logger.info("Starting Campus Assistant Bot...")
    logger.info("LLM Model: %s | Base URL: %s", config.LLM_MODEL, config.LLM_BASE_URL)
    start_health_server()

    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_todo))
    app.add_handler(CommandHandler("list", list_todos))
    app.add_handler(CommandHandler("done", done_todo))
    app.add_handler(CommandHandler("deltask", del_todo))
    app.add_handler(CommandHandler("events", events))
    app.add_handler(CommandHandler("profile", set_profile))
    app.add_handler(CommandHandler("myprofile", my_profile))
    app.add_handler(CommandHandler("match", match))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
