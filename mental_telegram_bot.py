import logging
import os
import random
import nltk
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ApplicationBuilder
from nltk.sentiment import SentimentIntensityAnalyzer
import threading

# Set up logging for debugging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


# Ensure NLTK dependencies are available
nltk.download("punkt")
nltk.download("vader_lexicon")

# Retrieve Telegram Bot Token from environment variable
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Please set your TELEGRAM_BOT_TOKEN environment variable.")

# Chatbot setup
sia = SentimentIntensityAnalyzer()

# Emotional categories with three different exercises each
exercises_by_emotion = {
    "anxiety": [
        "Try the *5-4-3-2-1* technique: Identify **5 things you see**, **4 you can touch**, **3 you hear**, **2 you smell**, **1 you taste.** Helps bring focus!",
        "Practice Box Breathing: Inhale for **4 seconds**, hold for **4 seconds**, exhale for **4 seconds**, hold for **4 seconds**—repeat 5 times.",
        "Say aloud: *“I am safe. I am capable. This feeling will pass.”* Repeat until you feel calmer."
    ],
    "stress": [
        "Take a **5-minute pause** and breathe deeply. If possible, step outside for fresh air—it resets your mind.",
        "Do Progressive Muscle Relaxation: Tighten different muscle groups (hands, shoulders, legs) for **5 seconds**, then release.",
        "Write down three things that went well today. A shift in focus can ease stress!"
    ],
    "sadness": [
        "Listen to your favorite uplifting song. Music has a profound impact on mood!",
        "Try a gratitude exercise: **Write down 5 things you're grateful for**—small joys matter!",
        "Perform one small act of kindness (a compliment, a thank-you message)—helping others lifts spirits."
    ],
    "motivation": [
        "Try the **two-minute rule**—if it takes **less than two minutes**, do it now!",
        "Visualize your future success. Picture achieving your goal and let that drive you!",
        "Break your task into **3 tiny steps**—starting small makes big goals easier to tackle."
    ],
    "loneliness": [
        "Reach out to a friend with a kind message. Connection eases isolation.",
        "Write down **3 things** you appreciate about yourself—remind yourself of your worth.",
        "Express emotions creatively—draw, write, sing—self-expression lessens loneliness."
    ],
    "anger": [
        "Picture a peaceful place—a forest, a beach. Close your eyes and imagine the calmness.",
        "Write down what's making you angry, then **tear up the paper**—symbolic destruction helps release emotions.",
        "Breathe deeply: Inhale for **6 seconds**, hold for **6 seconds**, exhale for **6 seconds**—repeat until you feel calmer."
    ],
    "confusion": [
        "Break the problem into **3 parts**: What do you know? What's unclear? What's **one action** you can take now?",
        "Imagine explaining the issue to **a friend**—how would they see it?",
        "Take a **short walk**, clear your mind, and return to the problem with fresh eyes."
    ]
}
stories_by_emotion = {
    "stress": [
        "💡 *The Wise Old Man* - A young man constantly complained about his life, always focusing on what he lacked. One day, an old man handed him a **🥤 half-filled glass** and said, *'Drink it or pour it away, but stop staring at what's missing.'* The young man realized that by obsessing over what he didn’t have, he was ignoring the blessings right in front of him.\n\n"
        "**💡 Moral:** *Gratitude shifts your perspective. Focus on what you have, not what you lack.*"
    ],
    "anxiety": [
        "💡 *The Elephant and the Rope* - A baby **🐘 elephant** was tied with a small rope to a wooden stake. As it grew, it never tried to break free, believing the rope still held it. In reality, the elephant had long since gained the **💪 strength** to escape, but its past experiences conditioned it to **never question its limits**.\n\n"
        "**💡 Moral:** *Don't let past limitations stop you from discovering your true strength.*"
    ],
    "sadness": [
        "💡 *The Small Candle* - In a **🌑 dark room**, a tiny **🕯️ candle** flickered alone, feeling insignificant. But as soon as it was lit, it filled the space with a **✨ warm glow**, proving that even the smallest light could brighten someone's world. It realized its value—no matter how small, it had the power to illuminate the darkness.\n\n"
        "**💡 Moral:** *Even small acts of kindness can make a big difference.*"
    ],
    "loneliness": [
        "💡 *The Boy and the Starfish* - A boy walked along a **🏝️ beach** covered with stranded **⭐ starfish**. One by one, he tossed them back into the ocean. A man approached him and said, *'You can’t possibly save them all.'* The boy smiled and replied, *'Maybe not, but I made a difference to that one.'*\n\n"
        "**💡 Moral:** *Small actions matter more than you think. Helping even one person can create a meaningful impact.*"
    ],
    "anger": [
        "💡 *The Resilient Bamboo* - During a **🌪️ fierce storm**, a tall, rigid **🌳 oak tree** stood firm—until it snapped under the wind’s pressure. Nearby, a **🎋 bamboo grove** bent gracefully with the storm, swaying with the wind instead of fighting against it. When the storm passed, the bamboo remained standing.\n\n"
        "**💡 Moral:** *Flexibility helps you endure life’s storms. Learning to adapt is the key to resilience.*"
    ],
    "confusion": [
        "💡 *The Two Seeds* - Two **🌱 seeds** lay side by side in the soil. One eagerly embraced the **🌿 earth**, stretched its roots, and sprouted into a **🌳 strong tree**. The other seed hesitated, fearing the **❓ unknown**, and remained buried forever. Its refusal to grow left it trapped, never knowing its true potential.\n\n"
        "**💡 Moral:** *Growth requires courage and stepping outside your comfort zone.*"
    ],
    "motivation": [
        "💡 *The Little Seed That Bloomed* - A **🌱 tiny seed** was planted in **🪨 rocky, dry soil**. Though conditions were harsh, it **☀️ pushed through obstacles**, sprouting little by little. With **🌿 patience and persistence**, the seed transformed into a vibrant, thriving **🌸 flower**—proof that **small efforts, when repeated, can lead to magnificent growth.**\n\n"
        "**💡 Moral:** *Persistence leads to success. Small steps, taken consistently, can create powerful transformations.*"
    ]
}

jokes = [
    "😂 *Why don’t scientists trust atoms?* Because they make up everything!",
    "😂 *I told my computer I needed a break,* now it keeps sending me KitKat ads!",
    "😂 *Why did the scarecrow win an award?* Because he was outstanding in his field!",
    "😂 *Why was the math book sad?* Because it had too many problems!"
]

# Function to detect emotions in user input
def detect_emotion(user_input):
    user_input = user_input.lower()
    emotions = {
        "anxiety": ["anxious", "nervous", "worried", "troubled", "disturbed"],
        "stress": ["stressed", "overwhelmed", "tensed"],
        "sadness": ["sad", "down", "miserable", "upset"],
        "motivation": ["unmotivated", "weak", "lazy"],
        "loneliness": ["lonely", "alone", "isolated", "abandoned"],
        "anger": ["angry", "furious", "frustrated", "annoyed"],
        "confusion": ["confused", "uncertain", "lost"]
    }
    for emotion, keywords in emotions.items():
        if any(word in user_input for word in keywords):
            return emotion
    return "neutral"

# Function to send chatbot response
async def message_handler(update: Update, context):
    # Send greeting message ONLY at the beginning of the conversation
    if "greeted" not in context.user_data:
        greeting_message = (
            "🌟 Hello! Welcome to Meha, your supportive mental health chatbot! 🌟\n\n"
            "I’m here to uplift and support you. Just tell me how you're feeling, "
            "and I’ll offer encouragement, exercises, and even jokes! Type how you're feeling, "
            "and let’s start a conversation. 💙"
        )
        await update.message.reply_text(greeting_message)
        context.user_data["greeted"] = True  # Prevent greeting from repeating

    user_message = update.message.text.lower()

    # Handle "quit" command
    if user_message == "quit":
        ending_message = "✨ **Remember, you're stronger than you think!** ✨\n\nEvery challenge is an opportunity for growth. Brighter days are ahead! 💙"
        await update.message.reply_text(ending_message)
        return

    # Detect emotion and provide varied exercises
    emotion = detect_emotion(user_message)
    if emotion in exercises_by_emotion:
        last_exercise = context.user_data.get(f"last_exercise_{emotion}", None)
        available_exercises = exercises_by_emotion[emotion]

        # Ensure a different exercise is chosen
        new_exercise = random.choice(available_exercises)
        while new_exercise == last_exercise:
            new_exercise = random.choice(available_exercises)

        context.user_data[f"last_exercise_{emotion}"] = new_exercise  # Store last used exercise

        await update.message.reply_text(f"{new_exercise}\n\n🌟 *Would you like a joke or maybe a story to cheer you up? Just say 'story', or 'joke'!* 😊")
        return

    # Handle jokes and stories
    if "joke" in user_message:
        await update.message.reply_text(f"{random.choice(jokes)}\n💡 *Want another joke? Just say 'joke'!* 😊")
        return
    if "story" in user_message:
        if emotion in stories_by_emotion:
            story = random.choice(stories_by_emotion[emotion])
        else:
            story = random.choice(sum(stories_by_emotion.values(), []))  
        await update.message.reply_text(f"{story}\n💡 *Want another uplifting story? Just say 'story'!* ✨")
        return

    # Default response
    await update.message.reply_text("Tell me more about how you're feeling. 💙")

# Telegram Bot setup
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Flask setup to keep Render awake
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Meha is running!"

def run_flask():
    PORT = int(os.getenv("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run Telegram polling in the main thread
    app.run_polling(drop_pending_updates=True)
