import discord
from discord.commands import slash_command, Option
from discord.ext import commands
import dotenv
import sqlite3
import os
import shutil
import aiofiles
import time


# Setting defaults
LOGO_LINK = "https://cdn.discordapp.com/attachments/797224818763104317/985818106989510666/shop.png"
sale_embed_template = """\

"""
order_embed_template = """\

"""


# Getting the database
base = sqlite3.connect(os.path.join(os.getcwd(), "base.db"))
cursor = base.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS guilds (guild_id INT, banker_role_id INT)")
cursor.execute("CREATE TABLE IF NOT EXISTS players (guild_id INT, balance INT)")
cursor.execute(
    "CREATE TABLE IF NOT EXISTS orders (guild_id INT, owner_id INT, item TEXT, quantity TEXT, commentary TEXT)"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS sales (guild_id INT, owner_id INT, item TEXT, quantity TEXT, \
    price TEXT, shop TEXT, commentary TEXT, in_stock BOOL NOT NULL CHECK (in_stock IN (0, 1)))"
)
# cursor.execute("INSERT INTO guilds (guild_id, banker_role_id) VALUES (?,?)", (795556636748021770, 988087004640182292)) # TEMP
base.commit()


# Creating bot
bot = discord.Bot(
    help_command=None,
    activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="звон алмазов"
    ),
    owner_id=689766059712315414
    # debug_guilds=[795556636748021770]  # TEMP
)


# Some useful fuctions
def get_time():  # for logging
    return time.strftime("%Y-%m-%d %X", time.gmtime()).split()


# Checks
def is_banker(ctx: discord.ApplicationContext) -> bool:
    cursor.execute("SELECT banker_role_id FROM guilds WHERE guild_id=?", (ctx.guild_id,))
    banker_role = ctx.guild.get_role(cursor.fetchone()[0])
    return banker_role in ctx.author.roles

moderator_permissions = discord.Permissions
moderator_permissions.manage_messages = True


# Modals
class SaleModal(discord.ui.Modal):
    def __init__(self,
                 item: str=None, quantity: str=None, price: str=None,
                 shop: str="Обращайтесь к продавцу", commentary: str=None) -> None:
        super().__init__(title="Объявление о продаже")
        
        self.add_item(
            discord.ui.InputText(
                label="Товар для продажи",
                placeholder="Название предмета",
                value=item
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Количество товара за транзакцию",
                placeholder='"480" или "7,5 стаков"',
                value=quantity
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Цена",
                placeholder='"5 алмазов" или "2 алмазных блока"',
                value=price
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Место совершения транзакции",
                placeholder="Координаты магазина",
                value=shop
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Комментарий",
                style=discord.InputTextStyle.long,
                required=False,
                value=commentary
            )
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        cursor.execute(
            "INSERT INTO sales (guild_id, owner_id, item, quantity, price, shop, commentary, in_stock) VALUES (?,?,?,?,?,?,?,?)",
            (interaction.guild_id, interaction.user.id, item := self.children[0].value, self.children[1].value,
             self.children[2].value, self.children[3].value, self.children[4].value, True)
        )
        base.commit()
        
        time = get_time()
        
        await interaction.edit_original_message(
            embed=discord.Embed(
                title="Объявление успешно создано",
                color=discord.Color.green()
            ),
            view=None
        )
        
        async with aiofiles.open(
            os.path.join("guild_logs", f"{interaction.guild_id}", f"{time[0]}.log"),
            "a",
            encoding="utf-8"
        ) as log:
            await log.write(f'[{time[1]}] {interaction.user} created SALE AD "{item}"\n')

class OrderModal(discord.ui.Modal):
    def __init__(self, item: str=None, quantity: str=None, commentary: str=None):
        super().__init__(title="Объявление о заказе")
        
        self.add_item(
            discord.ui.InputText(
                label="Заказываемый товар",
                placeholder="Название предмета",
                value=item
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Количество товара",
                placeholder='"480" или "7,5 стаков"',
                value=quantity
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Комментарий",
                style=discord.InputTextStyle.long,
                required=False,
                value=commentary
            )
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        cursor.execute(
            "INSERT INTO orders (guild_id, owner_id, item, quantity, commentary) VALUES (?,?,?,?,?)",
            (interaction.guild_id, interaction.user.id,
             item := self.children[0].value, self.children[1].value, self.children[2].value)
        )
        base.commit()
        
        await interaction.edit_original_message(
            embed=discord.Embed(
                title="Объявление успешно создано",
                color=discord.Color.green()
            ),
            view=None
        )
        
        async with aiofiles.open(
            os.path.join("guild_logs", f"{interaction.guild_id}", f"{time[0]}.log"),
            "a",
            encoding="utf-8"
        ) as log:
            await log.write(f'[{time[1]}] {interaction.user} created ORDER AD "{item}"\n')


# Views
class AdCreateView(discord.ui.View):
    @discord.ui.button(label="Продажа", emoji="💰", style=discord.ButtonStyle.green)
    async def sale(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(SaleModal())
    
    @discord.ui.button(label="Заказ", emoji="🛒", style=discord.ButtonStyle.green)
    async def order(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(OrderModal())

class AdEditView(discord.ui.View):
    pass


# Events
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:  # TEMP
        return
    
    if message.content.strip() == f"<@{bot.application_id}>":  # bot's mention
        await message.reply(
            embed=discord.Embed(
                title="Тут ничего нет",
                description="Может быть, когда-нибудь да будет..."
            )
        )
    
    await bot.process_application_commands(message)

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: Exception):
    if isinstance(error, discord.errors.CheckFailure):
        return
    else:
        raise error

@bot.event
async def on_guild_join(guild: discord.Guild):
    cursor.execute("INSERT INTO guilds VALUES (guild_id, banker_role_id)", (guild.id, None))
    base.commit()
    
    os.makedirs(os.path.join(os.getcwd(), "guild_logs", f"{guild.id}"))

@bot.event
async def on_guild_remove(guild: discord.Guild):
    cursor.execute("DELETE FROM guilds WHERE guild_id=?", (guild.id,))
    cursor.execute("DELETE FROM players WHERE guild_id=?", (guild.id,))
    cursor.execute("DELETE FROM sales WHERE guild_id=?", (guild.id,))
    cursor.execute("DELETE FROM orders WHERE guild_id=?", (guild.id,))
    base.commit()
    
    shutil.rmtree(os.path.join(os.getcwd(), "guild_logs", f"{guild.id}"))


# Slash groups
ad_group = bot.create_group("ad", "Действия с объявлениями")

@ad_group.command(description="Создать новое объявление")
async def create(ctx: discord.ApplicationContext):
    await ctx.respond(
        embed=discord.Embed(
            title="Новое объявление",
            description="Выберите тип",
            color=discord.Color.green()
        ),
        view=AdCreateView(),
        ephemeral=True
    )

@ad_group.command(description="Редактировать объявление")
async def edit(ctx: discord.ApplicationContext):
    pass

@ad_group.command(description="Снять объявление")
async def delete(ctx:discord.ApplicationContext):
    pass


# Cogs
class GeneralCommands(discord.Cog, name="General Commands"):
    """Commands available to everyone"""
    def __init__(self, bot: discord.Bot):
        self.bot = bot
    
    @slash_command(description="Показать список объявлений")
    async def store(self, ctx: discord.ApplicationContext):
        pass
    
    @slash_command(description="Узнать баланс")
    async def balance(
        self,
        ctx: discord.ApplicationContext,
        member: Option(discord.Member, "Участник сервера", required=False)
    ):
        member = member or ctx.author
    
    @slash_command(description="Перевести алмазы")
    async def transfer(self, ctx: discord.ApplicationContext):
        pass


class BankerCommands(discord.Cog, name="Banker Commands"):
    """Commands for bankers"""
    def __init__(self, bot: discord.Bot):
        self.bot = bot
    
    @slash_command(description="[Банкир] Управление счетами игроков")
    @commands.check(is_banker)
    async def deposit(self, ctx: discord.ApplicationContext):
        await ctx.respond("yup")
    

class ModeratorCommands(discord.Cog, name="Moderator Commands"):
    """Commands for moderators"""
    def __init__(self, bot: discord.Bot):
        self.bot = bot
    
    @slash_command(description="[Модератор] История действий")
    @commands.has_permissions(manage_messages=True)
    async def log(self, ctx: discord.ApplicationContext):
        pass  # чекнуть, за сколько дней есть логи, и вывести модал с выбором дня формата "2022-06-14"
    
    @slash_command(description="[Модератор] Настройка роли банкира")
    @commands.has_permissions(manage_messages=True)
    async def banker(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Роль банкира")
    ):
        await ctx.respond(role.mention)


# Adding cogs
bot.add_cog(GeneralCommands(bot))
bot.add_cog(BankerCommands(bot))
bot.add_cog(ModeratorCommands(bot))


# Getting the token and starting
dotenv.load_dotenv()
bot.run(os.getenv("TOKEN"))
