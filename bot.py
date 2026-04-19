import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import sys
from dotenv import load_dotenv

# 設定日誌格式與檔案名稱
# 檔案會存放在執行檔旁邊的 logs 資料夾內
if not os.path.exists('logs'):
    os.makedirs('logs')

log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'), # 寫入檔案
        logging.StreamHandler() # 同時顯示在終端機
    ]
)

logger = logging.getLogger('DiscordBot')

# 取得執行檔所在的目錄路徑
if getattr(sys, 'frozen', False):
    # exe
    application_path = os.path.dirname(sys.executable)
else:
    # .py
    application_path = os.path.dirname(os.path.abspath(__file__))

# 指定路徑讀取 .env
env_path = os.path.join(application_path, '.env')
load_dotenv(env_path)

TOKEN = os.getenv('DISCORD_TOKEN')

class BatchBan(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          # 必備：用於封鎖成員
        intents.message_content = True  # 選配：斜線指令其實不需要，但建議保留
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 這行會將斜線指令同步到 Discord
        # 注意：全域同步可能需要幾分鐘到一小時才會生效
        await self.tree.sync()
        logger.info("已同步斜線指令")

bot = BatchBan()

@bot.event
async def on_ready():
    logger.info(f"機器人已上線：{bot.user}")

# 定義斜線指令
@bot.tree.command(name="multiban", description="批次封鎖多個使用者")
@app_commands.describe(
    uids="請輸入 ids 並用分號分隔 (例如: uId1;uId2;uId3)",
    reason="封鎖原因(選填)"
)
@app_commands.checks.has_permissions(ban_members=True)
async def multiban(interaction: discord.Interaction, uids: str, reason: str = "批次封鎖"):
    logger.info(f"執行者: {interaction.user} | 指令參數: {uids}")
    user_ids = uids.split(';')
    success_count = 0
    fail_count = 0
    await interaction.response.send_message(f"開始處理 {len(user_ids)} 個帳號的停權流程...原因：{reason} 需等待約 {len(user_ids)} 秒。原因：{reason}", ephemeral=True)
    logger.info(f"開始處理 {len(user_ids)} 個帳號的停權流程...原因：{reason} 需等待約 {len(user_ids)} 秒。原因：{reason}")

    for user_id in user_ids:
        user_id = user_id.strip()
        if not user_id:
            continue
        try:
            # 嘗試轉換並獲取使用者物件
            user = await bot.fetch_user(int(user_id))
            await interaction.guild.ban(user, reason=f"原因：{reason} | by {interaction.user}")
            logger.info(f"{user} 停權成功")
            success_count += 1
            await asyncio.sleep(1) # 防頻率限制
        except Exception as e:
            logger.error(f"執行發生錯誤: {e}", exc_info=True)
            fail_count += 1

    # 更新原始回覆訊息
    await interaction.edit_original_response(
        content=f"✅ 操作完成！\n成功封鎖：{success_count} 個\n失敗：{fail_count} 個"
    )
    logger.info(f"操作完成，成功：{success_count} 人，失敗：{fail_count} 人")

# 錯誤處理（例如使用者沒有權限時）
@multiban.error
async def multiban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ 你沒有權限執行此指令！", ephemeral=True)

if __name__ == "__main__":
    try:
        if TOKEN:
            logger.info("正在嘗試登入 Discord...")
            bot.run(TOKEN)
        else:
            logger.error("❌ 找不到 DISCORD_TOKEN，請檢查 .env 檔案路徑與內容。")
            input("按任意鍵退出...")
    except discord.errors.LoginFailure:
        logger.error("❌ Token 無效，請確認 .env 中的 Token 是否正確。")
        input("按任意鍵退出...")
    except discord.errors.PrivilegedIntentsRequired:
        logger.error("❌ 權限不足！請前往 Developer Portal 開啟 'Server Members Intent'。")
        input("按任意鍵退出...")
    except Exception as e:
        logger.critical(f"🚀 機器人崩潰: {e}", exc_info=True)
        input("按任意鍵退出...")