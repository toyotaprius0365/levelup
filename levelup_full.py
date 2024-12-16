import discord
from discord.ext import commands
import json
import os
import datetime

TOKEN = "YOUR DISCORD BOT TOKEN HERE!"
version = "1.1.2"

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
		user_data[user_id]["username"] = username

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

@bot.tree.command(name="leaderboard", description="See the server's XP leaderboard!")
async def leaderboard(interaction: discord.Interaction):
	sorted_users = sorted(user_data.items(), key=lambda x: x[1]["level"], reverse=True)
	top_users = sorted_users[:10]
	leaderboard = "\n".join(
		[f"{i+1}. {user[1]['username']} - Level {user[1]['level']} ({user[1]['xp']} XP) - 🔥{user[1]['daily_streak']}-day streak" for i, user in enumerate(top_users)]
	)
	await interaction.response.send_message(f"**XP Leaderboard:**\n{leaderboard}")

@bot.tree.command(name="daily", description="Use this command to receive your daily reward!")
async def daily_reward(interaction: discord.Interaction):
	try:
		user_id = str(interaction.user.id)
		now = datetime.datetime.now().date()
		print(f"NOTICE: {now} | datetime acquired")

		load_data()

		if user_id not in user_data:
			user_data[user_id] = {"username": str(interaction.user), "xp": 0, "level": 1, "daily_reward_claimed": None, "daily_streak": 0}

		last_claim_date = user_data[user_id].get("daily_reward_claimed")
		daily_streak = user_data[user_id].get("daily_streak", 0)

		# parse last claim date if it exists
		if last_claim_date:
			try:
				last_claim_date = datetime.datetime.strptime(last_claim_date, "%Y-%m-%d").date()
			except ValueError:
				print(f"ERROR: Invalid date format for {user_id}, resetting.")
				last_claim_date = None
				user_data[user_id]["daily_reward_claimed"] = None
				user_data[user_id]["daily_streak"] = 0

		# check if user is eligible to claim a daily reward
		if last_claim_date and (now - last_claim_date).days < 1:
			remaining_time = 24 - (now - last_claim_date).seconds // 3600
			await interaction.response.send_message(f"{interaction.user.mention}, you can claim your daily reward again in {remaining_time} Hours.")
			return

		if last_claim_date:
			days_since_last_claim = (now - last_claim_date).days
			if days_since_last_claim == 1:
				daily_streak += 1
			elif days_since_last_claim > 1:
				daily_streak = 1
		else:
			daily_streak = 1

		if daily_streak > 7:
			daily_streak = 7

		xp_reward = 50 * daily_streak
		user_data[user_id]["xp"] += xp_reward
		user_data[user_id]["daily_reward_claimed"] = now.strftime("%Y-%m-%d")
		user_data[user_id]["daily_streak"] = daily_streak

		save_data()

		await interaction.response.send_message(
			f"{interaction.user.mention}, you claimed your daily reward of {xp_reward} XP! "
			f"You are on a 🔥 {daily_streak}-day streak! ")
		print(f"NOTICE: Awarded {interaction.user.name} with {xp_reward} XP (streak: {daily_streak} days)")

	except Exception as e:
		import traceback
		print(f"ERROR: /daily command cannot function: {e}")
		traceback.print_exc()
		await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        print(f"NOTICE: Interaction received: {interaction.data}")

bot.run(TOKEN)