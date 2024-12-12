import discord
from discord.ext import commands
import json
import os

TOKEN = "YOUR DISCORD BOT TOKEN HERE"
version = "1.0.2"

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_data = {}

def load_data():
	global user_data
	if os.path.exists("data.json"):
		with open("data.json", "r") as f:
			user_data = json.load(f)

def save_data():
	with open("data.json", "w") as f:
		json.dump(user_data, f, indent=4)

def xp_for_next_level(level):
	return int(100 * (level ** 1.5))

async def assign_colored_role(member, level):
	role_name = f"Level {level}"

	role = discord.utils.get(member.guild.roles, name=role_name)
	if role:
		if role not in member.roles:
			try:
				await member.add_roles(role)
				print(f"NOTICE: Assigned {role.name} to {member.name}")
			except discord.Forbidden:
				print(f"ERROR: Not enough permissions, Unable to assign {role.name} to {member.name}")
			except discord.HTTPException as e:
				print(e)
	else:
		print(f"NOTICE: Role '{role_name}' not found in the server roles.")

@bot.event
async def on_ready():
	print(f"Current Version: {version}")
	print(f"NOTICE: Logged in as {bot.user}!")
	load_data()

	for guild in bot.guilds:
		await create_default_roles(guild)

	try:
		synced = await bot.tree.sync()
		print(f"NOTICE: synced {len(synced)} application commands!")
	except Exception as e:
		print(f"ERROR: Failed to sync commands: {e}")

	activity = discord.Game("⚠️ Use /level to check your level! ⚠️")
	await bot.change_presence(status=discord.Status.online, activity=activity)

async def create_default_roles(guild):
	
	for level in range(10, 101, 10): # levels 10 to 100
		role_name = f"Level {level}"
		existing_role = discord.utils.get(guild.roles, name=role_name)
		if not existing_role:
			try:
				color = discord.Color.random()
				await guild.create_role(name=role_name, color=color, reason="Default level role creation")
				print(f"NOTICE: Role {role_name} created in {guild.name}!")
			except discord.Forbidden:
				print(f"ERROR: Not enough permissions, Unable to assign {role.name} to {member.name}")
			except discord.HTTPException as e:
				print(e)
		else:
			print(f"NOTICE: Role {role_name} already exists in {guild.name}, skipping creation!")		

@bot.event
async def on_message(message):
	if message.author.bot:
		return # ignore bot messages

	user_id = str(message.author.id)
	username = str(message.author)

	if user_id not in user_data:
		user_data[user_id] = {"username": username, "xp": 0, "level": 1}
	else:
		if "username" not in user_data[user_id]:
			user_data[user_id]["username"] = username

	# update username if it changed
	if user_data[user_id]["username"] != username:
		user_data[user_id][username] = username

	user_data[user_id]["xp"] += 10
	current_xp = user_data[user_id]["xp"]
	current_level = user_data[user_id]["level"]

	while current_xp >= xp_for_next_level(current_level) and current_level < 100:
		current_xp -= xp_for_next_level(current_level)
		current_level += 1
		await message.channel.send(f"{message.author.mention} leveled up to Level {current_level}!")

		if current_level % 10 == 0:
			member = message.author
			await assign_colored_role(member, current_level)

	user_data[user_id]["xp"] = current_xp
	user_data[user_id]["level"] = current_level

	save_data()

	await bot.process_commands(message)

@bot.tree.command(name="level", description="Check your level and XP!")
async def check_level(interaction: discord.Interaction):
	user_id = str(interaction.user.id)
	if user_id not in user_data:
		await interaction.response.send_message("You have no XP yet, start chatting to earn some!")
	else:
		level = user_data[user_id]["level"]
		xp = user_data[user_id]["xp"]
		xp_next = xp_for_next_level(level)
		await interaction.response.send_message(f"{interaction.user.mention}, you are Level {level} with {xp}/{xp_next} XP.") # ephemeral=True was deleted

bot.run(TOKEN)