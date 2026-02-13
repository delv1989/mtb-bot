import asyncio
import os
import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
import whisper
from gtts import gTTS

# Инициализация бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загружаем модель Whisper (base ~150MB)
# Варианты: tiny (40MB), base (150MB), small (500MB), medium (1.5GB)
model = whisper.load_model("base")

print("✅ Бот запущен! Модель Whisper загружена.")

@dp.message()
async def handle_message(message: types.Message):
    """Обработчик всех сообщений"""
    
    # Если голосовое сообщение - распознаем
    if message.voice or message.audio:
        await handle_voice(message)
        return
    
    # Обычный текст
    user_text = message.text
    print(f"📨 Сообщение от {message.from_user.username}: {user_text}")
    
    # Генерируем ответ (здесь можно добавить AI логику)
    response_text = f"Привет! Я получил: {user_text}"
    
    # Отправляем голосовым
    await send_voice_response(message, response_text)

async def handle_voice(message: types.Message):
    """Распознавание голосового сообщения"""
    
    # Скачиваем голосовое
    voice = message.voice or message.audio
    voice_file = await bot.get_file(voice.file_id)
    
    # Сохраняем временно
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_ogg:
        await bot.download_file(voice_file.file_path, tmp_ogg.name)
        
        # Конвертируем в wav (Whisper лучше понимает)
        tmp_wav = tmp_ogg.name.replace(".ogg", ".wav")
        os.system(f"ffmpeg -i {tmp_ogg.name} -ar 16000 -ac 1 -c:a pcm_s16le {tmp_wav} -y 2>/dev/null")
        
        # Распознаем
        try:
            result = model.transcribe(tmp_wav, language="ru")
            recognized_text = result["text"]
            
            # Отвечаем распознанным текстом
            await message.reply(f"🎙️ Распознано: {recognized_text}")
            
            # И голосовым ответом
            response = f"Вы сказали: {recognized_text}"
            await send_voice_response(message, response)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка распознавания: {str(e)}")
        
        finally:
            # Чистим временные файлы
            if os.path.exists(tmp_ogg.name):
                os.unlink(tmp_ogg.name)
            if os.path.exists(tmp_wav):
                os.unlink(tmp_wav)

async def send_voice_response(message: types.Message, text: str):
    """Отправка голосового ответа"""
    
    try:
        # Генерируем голос (gTTS - бесплатно)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
            # Ограничиваем длину текста
            text_short = text[:500] if len(text) > 500 else text
            
            tts = gTTS(text=text_short, lang='ru')
            tts.save(tmp_mp3.name)
            
            # Отправляем
            await message.answer_voice(voice=FSInputFile(tmp_mp3.name))
            
            # Удаляем файл
            os.unlink(tmp_mp3.name)
            
    except Exception as e:
        # Если TTS не сработал - отправляем текст
        await message.reply(f"📝 {text}")
        print(f"TTS ошибка: {e}")

async def main():
    print("🤖 Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
