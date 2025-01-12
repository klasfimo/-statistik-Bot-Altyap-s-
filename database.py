import aiosqlite
import datetime
from typing import Optional, List, Dict
import matplotlib.pyplot as plt
import io

class Database:
    def __init__(self, db_name: str = "discord_stats.db"):
        self.db_name = db_name

    async def setup(self):
        """Veritabanı tablolarını oluştur"""
        async with aiosqlite.connect(self.db_name) as db:
            # Mesaj tablosu
            await db.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id INTEGER,
                    guild_id INTEGER,
                    timestamp DATETIME,
                    content_length INTEGER
                )
            ''')

            # Sesli kanal tablosu
            await db.execute('''
                CREATE TABLE IF NOT EXISTS voice_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id INTEGER,
                    guild_id INTEGER,
                    join_time DATETIME,
                    leave_time DATETIME
                )
            ''')

            # Emoji tablosu
            await db.execute('''
                CREATE TABLE IF NOT EXISTS emoji_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    emoji_id TEXT,
                    emoji_name TEXT,
                    timestamp DATETIME
                )
            ''')

            # Rol tablosu
            await db.execute('''
                CREATE TABLE IF NOT EXISTS role_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    role_id INTEGER,
                    action TEXT,
                    timestamp DATETIME
                )
            ''')

            # Seviye tablosu
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_levels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    last_message_time DATETIME
                )
            ''')

            # Haftalık periyot tablosu
            await db.execute('''
                CREATE TABLE IF NOT EXISTS weekly_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time DATETIME,
                    end_time DATETIME,
                    is_current BOOLEAN DEFAULT 0
                )
            ''')

            # Kalıcı istatistik tablosu
            await db.execute('''
                CREATE TABLE IF NOT EXISTS permanent_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    total_messages INTEGER DEFAULT 0,
                    total_voice_minutes INTEGER DEFAULT 0,
                    last_updated DATETIME,
                    UNIQUE(user_id, guild_id)
                )
            ''')

            await db.commit()

    async def log_message(self, user_id: int, channel_id: int, guild_id: int, timestamp: datetime.datetime):
        """Mesaj kayıtlarını tut"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                INSERT INTO messages (user_id, channel_id, guild_id, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (user_id, channel_id, guild_id, timestamp))
            await db.commit()

    async def log_voice_join(self, user_id: int, channel_id: int, guild_id: int, timestamp: datetime.datetime):
        """Sesli kanala katılma kaydı"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                INSERT INTO voice_activity (user_id, channel_id, guild_id, join_time)
                VALUES (?, ?, ?, ?)
            ''', (user_id, channel_id, guild_id, timestamp))
            await db.commit()

    async def log_voice_leave(self, user_id: int, channel_id: int, guild_id: int, timestamp: datetime.datetime):
        """Sesli kanaldan ayrılma kaydı"""
        async with aiosqlite.connect(self.db_name) as db:
            # En son giriş kaydını bul ve çıkış zamanını güncelle
            await db.execute('''
                UPDATE voice_activity
                SET leave_time = ?
                WHERE user_id = ? AND channel_id = ? AND guild_id = ? AND leave_time IS NULL
            ''', (timestamp, user_id, channel_id, guild_id))
            await db.commit()

    async def get_message_count(self, guild_id: int, period: str = 'günlük') -> int:
        """Belirli bir periyottaki mesaj sayısını getir"""
        async with aiosqlite.connect(self.db_name) as db:
            now = datetime.datetime.now()
            if period == 'günlük':
                start_time = now - datetime.timedelta(days=1)
            elif period == 'haftalık':
                start_time = now - datetime.timedelta(weeks=1)
            elif period == 'aylık':
                start_time = now - datetime.timedelta(days=30)
            else:
                start_time = datetime.datetime.min

            async with db.execute('''
                SELECT COUNT(*) FROM messages
                WHERE guild_id = ? AND timestamp > ?
            ''', (guild_id, start_time)) as cursor:
                count = await cursor.fetchone()
                return count[0] if count else 0

    async def get_active_users_count(self, guild_id: int, period: str = 'günlük') -> int:
        """Aktif kullanıcı sayısını getir"""
        async with aiosqlite.connect(self.db_name) as db:
            now = datetime.datetime.now()
            if period == 'günlük':
                start_time = now - datetime.timedelta(days=1)
            elif period == 'haftalık':
                start_time = now - datetime.timedelta(weeks=1)
            elif period == 'aylık':
                start_time = now - datetime.timedelta(days=30)
            else:
                start_time = datetime.datetime.min

            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) FROM messages
                WHERE guild_id = ? AND timestamp > ?
            ''', (guild_id, start_time)) as cursor:
                count = await cursor.fetchone()
                return count[0] if count else 0

    async def get_user_message_count(self, user_id: int, guild_id: int) -> int:
        """Kullanıcının toplam mesaj sayısını getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT COUNT(*) FROM messages
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id)) as cursor:
                count = await cursor.fetchone()
                return count[0] if count else 0

    async def get_user_voice_time(self, user_id: int, guild_id: int) -> int:
        """Kullanıcının toplam sesli kanal süresini dakika cinsinden getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT SUM(
                    CAST(
                        (JULIANDAY(COALESCE(leave_time, CURRENT_TIMESTAMP)) - 
                         JULIANDAY(join_time)) * 24 * 60 AS INTEGER)
                    )
                FROM voice_activity
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id)) as cursor:
                minutes = await cursor.fetchone()
                return minutes[0] if minutes and minutes[0] else 0 

    async def log_emoji_usage(self, user_id: int, guild_id: int, emoji_id: str, emoji_name: str):
        """Emoji kullanımını kaydet"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                INSERT INTO emoji_usage (user_id, guild_id, emoji_id, emoji_name, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, guild_id, emoji_id, emoji_name, datetime.datetime.now()))
            await db.commit()

    async def log_role_change(self, user_id: int, guild_id: int, role_id: int, action: str):
        """Rol değişikliklerini kaydet"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                INSERT INTO role_history (user_id, guild_id, role_id, action, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, guild_id, role_id, action, datetime.datetime.now()))
            await db.commit()

    async def update_user_xp(self, user_id: int, guild_id: int, xp_amount: float = None):
        """Kullanıcı XP'sini güncelle ve seviye kontrolü yap"""
        async with aiosqlite.connect(self.db_name) as db:
            # XP miktarı belirtilmemişse, sunucunun XP oranını kullan
            if xp_amount is None:
                xp_amount = await self.get_xp_rate(guild_id)

            # Kullanıcıyı kontrol et veya oluştur
            await db.execute('''
                INSERT OR IGNORE INTO user_levels (user_id, guild_id, xp, level)
                VALUES (?, ?, 0, 0)
            ''', (user_id, guild_id))

            # XP'yi güncelle
            await db.execute('''
                UPDATE user_levels
                SET xp = ROUND(xp + ?, 2),
                    last_message_time = ?
                WHERE user_id = ? AND guild_id = ?
            ''', (xp_amount, datetime.datetime.now(), user_id, guild_id))

            # Seviye kontrolü
            async with db.execute('''
                SELECT xp, level FROM user_levels
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id)) as cursor:
                data = await cursor.fetchone()
                if data:
                    current_xp, current_level = data
                    new_level = int(current_xp / 100)  # Her 100 XP'de bir seviye
                    if new_level > current_level:
                        await db.execute('''
                            UPDATE user_levels
                            SET level = ?
                            WHERE user_id = ? AND guild_id = ?
                        ''', (new_level, user_id, guild_id))
                        await db.commit()
                        return True, new_level
            await db.commit()
            return False, 0

    async def get_user_level(self, user_id: int, guild_id: int) -> tuple:
        """Kullanıcının seviye bilgilerini getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT xp, level FROM user_levels
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id)) as cursor:
                data = await cursor.fetchone()
                return data if data else (0, 0)

    async def get_top_users(self, guild_id: int, limit: int = 10) -> List[tuple]:
        """En yüksek seviyeli kullanıcıları getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT user_id, xp, level FROM user_levels
                WHERE guild_id = ?
                ORDER BY level DESC, xp DESC
                LIMIT ?
            ''', (guild_id, limit)) as cursor:
                return await cursor.fetchall()

    async def generate_activity_graph(self, guild_id: int, days: int = 7) -> io.BytesIO:
        """Sunucu aktivite grafiği oluştur"""
        async with aiosqlite.connect(self.db_name) as db:
            start_date = datetime.datetime.now() - datetime.timedelta(days=days)
            async with db.execute('''
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM messages
                WHERE guild_id = ? AND timestamp > ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (guild_id, start_date)) as cursor:
                data = await cursor.fetchall()
                
                dates = [row[0] for row in data]
                counts = [row[1] for row in data]

                plt.figure(figsize=(10, 6))
                plt.plot(dates, counts, marker='o')
                plt.title('Sunucu Aktivite Grafiği')
                plt.xlabel('Tarih')
                plt.ylabel('Mesaj Sayısı')
                plt.xticks(rotation=45)
                plt.tight_layout()

                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                plt.close()
                
                return buf

    async def get_emoji_stats(self, guild_id: int) -> Dict:
        """Emoji kullanım istatistiklerini getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT emoji_name, COUNT(*) as count
                FROM emoji_usage
                WHERE guild_id = ?
                GROUP BY emoji_name
                ORDER BY count DESC
                LIMIT 10
            ''', (guild_id,)) as cursor:
                return {row[0]: row[1] for row in await cursor.fetchall()} 

    async def get_channel_stats(self, channel_id: int, guild_id: int, period: str = 'günlük') -> Dict:
        """Kanal istatistiklerini detaylı olarak getir"""
        async with aiosqlite.connect(self.db_name) as db:
            now = datetime.datetime.now()
            if period == 'günlük':
                start_time = now - datetime.timedelta(days=1)
            elif period == 'haftalık':
                start_time = now - datetime.timedelta(weeks=1)
            elif period == 'aylık':
                start_time = now - datetime.timedelta(days=30)
            else:
                start_time = datetime.datetime.min

            stats = {}
            
            # Mesaj sayısı
            async with db.execute('''
                SELECT COUNT(*) FROM messages
                WHERE channel_id = ? AND guild_id = ? AND timestamp > ?
            ''', (channel_id, guild_id, start_time)) as cursor:
                stats['message_count'] = (await cursor.fetchone())[0]

            # Aktif kullanıcılar
            async with db.execute('''
                SELECT COUNT(DISTINCT user_id) FROM messages
                WHERE channel_id = ? AND guild_id = ? AND timestamp > ?
            ''', (channel_id, guild_id, start_time)) as cursor:
                stats['active_users'] = (await cursor.fetchone())[0]

            # En aktif saatler
            async with db.execute('''
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM messages
                WHERE channel_id = ? AND guild_id = ? AND timestamp > ?
                GROUP BY hour
                ORDER BY count DESC
                LIMIT 5
            ''', (channel_id, guild_id, start_time)) as cursor:
                stats['peak_hours'] = await cursor.fetchall()

            # En aktif kullanıcılar
            async with db.execute('''
                SELECT user_id, COUNT(*) as count
                FROM messages
                WHERE channel_id = ? AND guild_id = ? AND timestamp > ?
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT 5
            ''', (channel_id, guild_id, start_time)) as cursor:
                stats['top_users'] = await cursor.fetchall()

            return stats

    async def get_voice_leaderboard(self, guild_id: int, period: str = 'günlük') -> List[tuple]:
        """Sesli kanal sıralamasını getir"""
        async with aiosqlite.connect(self.db_name) as db:
            now = datetime.datetime.now()
            
            if period == 'haftalık':
                # Mevcut haftalık periyodu al
                period_data = await self.get_current_weekly_period()
                if period_data:
                    start_time = period_data[0]
                else:
                    # Periyot yoksa varsayılan olarak son 7 gün
                    start_time = now - datetime.timedelta(weeks=1)
            elif period == 'günlük':
                start_time = now - datetime.timedelta(days=1)
            elif period == 'aylık':
                start_time = now - datetime.timedelta(days=30)
            else:
                start_time = datetime.datetime.min

            async with db.execute('''
                SELECT 
                    user_id,
                    SUM(
                        CAST(
                            (JULIANDAY(COALESCE(leave_time, CURRENT_TIMESTAMP)) - 
                             JULIANDAY(join_time)) * 24 * 60 AS INTEGER
                        )
                    ) as total_minutes
                FROM voice_activity
                WHERE guild_id = ? AND join_time > ?
                GROUP BY user_id
                ORDER BY total_minutes DESC
                LIMIT 10
            ''', (guild_id, start_time)) as cursor:
                return await cursor.fetchall()

    async def get_message_leaderboard(self, guild_id: int, period: str = 'günlük') -> List[tuple]:
        """Mesaj sıralamasını getir"""
        async with aiosqlite.connect(self.db_name) as db:
            now = datetime.datetime.now()
            if period == 'günlük':
                start_time = now - datetime.timedelta(days=1)
            elif period == 'haftalık':
                start_time = now - datetime.timedelta(weeks=1)
            elif period == 'aylık':
                start_time = now - datetime.timedelta(days=30)
            else:
                start_time = datetime.datetime.min

            async with db.execute('''
                SELECT user_id, COUNT(*) as message_count
                FROM messages
                WHERE guild_id = ? AND timestamp > ?
                GROUP BY user_id
                ORDER BY message_count DESC
                LIMIT 10
            ''', (guild_id, start_time)) as cursor:
                return await cursor.fetchall() 

    async def update_weekly_period(self):
        """Haftalık periyodu güncelle"""
        async with aiosqlite.connect(self.db_name) as db:
            now = datetime.datetime.now()
            # Pazar günü 23:30'u bul
            days_until_sunday = (6 - now.weekday()) % 7
            next_sunday = now + datetime.timedelta(days=days_until_sunday)
            period_end = next_sunday.replace(hour=23, minute=30, second=0, microsecond=0)
            period_start = period_end - datetime.timedelta(days=7)

            # Mevcut periyodu kontrol et
            async with db.execute('SELECT id FROM weekly_periods WHERE is_current = 1') as cursor:
                current_period = await cursor.fetchone()
                if current_period:
                    # Mevcut periyodu güncelle
                    await db.execute('UPDATE weekly_periods SET is_current = 0 WHERE id = ?', (current_period[0],))

            # Yeni periyot oluştur
            await db.execute('''
                INSERT INTO weekly_periods (start_time, end_time, is_current)
                VALUES (?, ?, 1)
            ''', (period_start, period_end))
            
            await db.commit()

    async def get_current_weekly_period(self) -> tuple:
        """Mevcut haftalık periyodu getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT start_time, end_time FROM weekly_periods
                WHERE is_current = 1
            ''') as cursor:
                return await cursor.fetchone()

    async def update_permanent_stats(self, user_id: int, guild_id: int, messages: int = 0, voice_minutes: int = 0):
        """Kalıcı istatistikleri güncelle"""
        async with aiosqlite.connect(self.db_name) as db:
            # Önce kullanıcı var mı kontrol et
            async with db.execute('''
                SELECT id FROM permanent_stats 
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id)) as cursor:
                user_exists = await cursor.fetchone()

            if user_exists:
                # Kullanıcı varsa güncelle
                await db.execute('''
                    UPDATE permanent_stats 
                    SET total_messages = total_messages + ?,
                        total_voice_minutes = total_voice_minutes + ?,
                        last_updated = ?
                    WHERE user_id = ? AND guild_id = ?
                ''', (messages, voice_minutes, datetime.datetime.now(), user_id, guild_id))
            else:
                # Kullanıcı yoksa yeni kayıt oluştur
                await db.execute('''
                    INSERT INTO permanent_stats 
                    (user_id, guild_id, total_messages, total_voice_minutes, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, guild_id, messages, voice_minutes, datetime.datetime.now()))

            await db.commit()

    async def get_permanent_stats(self, guild_id: int, limit: int = 10) -> List[tuple]:
        """Kalıcı istatistikleri getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT user_id, total_messages, total_voice_minutes
                FROM permanent_stats
                WHERE guild_id = ?
                ORDER BY (total_messages + total_voice_minutes) DESC
                LIMIT ?
            ''', (guild_id, limit)) as cursor:
                return await cursor.fetchall() 

    async def reset_user_stats(self, user_id: int, guild_id: int):
        """Kullanıcının tüm istatistiklerini sıfırla"""
        async with aiosqlite.connect(self.db_name) as db:
            # Mesajları sil
            await db.execute('DELETE FROM messages WHERE user_id = ? AND guild_id = ?', 
                           (user_id, guild_id))
            
            # Sesli aktiviteleri sil
            await db.execute('DELETE FROM voice_activity WHERE user_id = ? AND guild_id = ?', 
                           (user_id, guild_id))
            
            # Emoji kullanımlarını sil
            await db.execute('DELETE FROM emoji_usage WHERE user_id = ? AND guild_id = ?', 
                           (user_id, guild_id))
            
            # Seviye bilgilerini sıfırla
            await db.execute('''
                UPDATE user_levels 
                SET xp = 0, level = 0 
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            
            # Kalıcı istatistikleri sıfırla
            await db.execute('''
                UPDATE permanent_stats 
                SET total_messages = 0, total_voice_minutes = 0 
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            
            await db.commit()

    async def reset_period_stats(self, guild_id: int, period_type: str):
        """Belirli bir periyodun istatistiklerini sıfırla"""
        async with aiosqlite.connect(self.db_name) as db:
            now = datetime.datetime.now()
            
            if period_type == 'haftalık':
                start_time = now - datetime.timedelta(weeks=1)
            elif period_type == 'aylık':
                start_time = now - datetime.timedelta(days=30)
            else:
                return
            
            # Mesajları sil
            await db.execute('''
                DELETE FROM messages 
                WHERE guild_id = ? AND timestamp > ?
            ''', (guild_id, start_time))
            
            # Sesli aktiviteleri sil
            await db.execute('''
                DELETE FROM voice_activity 
                WHERE guild_id = ? AND join_time > ?
            ''', (guild_id, start_time))
            
            await db.commit()

    async def update_xp_rate(self, guild_id: int, xp_rate: float):
        """XP kazanma oranını güncelle"""
        async with aiosqlite.connect(self.db_name) as db:
            # XP oranları tablosunu oluştur (eğer yoksa)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS xp_rates (
                    guild_id INTEGER PRIMARY KEY,
                    xp_per_message REAL DEFAULT 10.0
                )
            ''')
            
            # XP oranını güncelle veya ekle
            await db.execute('''
                INSERT OR REPLACE INTO xp_rates (guild_id, xp_per_message)
                VALUES (?, ?)
            ''', (guild_id, xp_rate))
            
            await db.commit()

    async def get_xp_rate(self, guild_id: int) -> float:
        """Sunucunun XP kazanma oranını getir"""
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute('''
                SELECT xp_per_message FROM xp_rates WHERE guild_id = ?
            ''', (guild_id,)) as cursor:
                result = await cursor.fetchone()
                return float(result[0]) if result else 10.0  # Varsayılan: 10.0 XP 