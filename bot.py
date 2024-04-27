from xml.etree.ElementPath import get_parent_map
from discord.ext import commands, tasks
from colorama import init
import aiosqlite
import requests, httpx
import discord
import sys
import os
import asyncio
import io
from utils import get_config, update_token, log, GREEN, get_txids, get_confirmations,getstats
from utils import restart as restart_all_vps
from datetime import datetime
import toml


try:
    config = toml.load("bot_strings.toml")
except Exception as E:
    log(f"Could not load the bot_strings.toml file.\n{E}")
    x = os._exit(1)

try:
    embed_color = config['embed_color']
    error_color = config['error_color']
    ticket_emb_title = config['ticket_emb_title']
    ticket_emb_desc = config['ticket_emb_desc']
    queue_msg_title = config['queue_msg_title']
    queue_msg_footer = config['queue_msg_footer']
    queue_msg_desc = config['queue_msg_desc']
    not_number_error_title = config['not_number_error_title']
    not_number_error_description = config['not_number_error_description']
    new_order_reaction = config['new_order_reaction']
    new_ticket_manager_title = config['new_ticket_manager_title']
    new_ticket_manager_desc = config['new_ticket_manager_desc']
    new_ticket_msg_title = config['new_ticket_msg_title']
    new_ticket_msg_desc = config['new_ticket_msg_desc']
    claims_ticket_title = config['claims_ticket_title']
    claims_ticket_desc = config['claims_ticket_desc']
    payment_choice_title = config['payment_choice_title']
    payment_choice_desc = config['payment_choice_desc']
    send_paypal_title = config['send_paypal_title']
    send_paypal_desc = config['send_paypal_desc']
    claims_ticket_cryptos = config['claims_ticket_cryptos']
    payment_msg_title = config['payment_msg_title']
    payment_msg_desc = config['payment_msg_desc']
    txid_title = config['txid_title']
    txid_desc = config['txid_desc']
    send_token_title = config['send_token_title']
    send_token_desc = config['send_token_desc']
    channel_id_sniped = config['claimed_channel']
except:
    log("A parameter is missing in bot_strings.toml")
    x = os._exit(1)

set_bot = None

VERSION = "1"
TITLE = f"Queue Bot v{VERSION}"

vps_ip, vps_user, vps_pass, prefix, queue_channel_id, queue_message_id, success_msg_channel, send_success_msg, embed_success_msg, ping_role, success_msg_boost, token, transcript_channel_id, ticket_category_id, claim_price, queue_message_inactive, queue_message_active, success_msg_classic, success_msg_basic, vps_delay, green_queue_emoji, red_queue_emoji, paypal_payments, paypal_address, paypal_password = "", "", "", ".", 1, 1, 1, True, True, True, "", "", None, None, 0, "", "", "", "", 0, "", "", False, "", ""

if sys.platform == "darwin":
    sys.stdout.write(f"\x1b]2;{TITLE}\x07")

elif "win" in sys.platform:
    os.system("title " + TITLE)
    init(convert=True)


def doExit():
    try:
        input("")
    except:
        pass

    sys.exit(0)


def load_config():
    for key, value in get_config():
        if value is None: value = None
        if isinstance(value, str):
            if value.lower() == "true": value = True
            elif value.lower() == "false": value = False
        globals().__setitem__(key, value)


load_config()

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=prefix,
                   case_insensitive=True,
                   intents=intents)
bot.remove_command('help')

ticket_emb = discord.Embed(title=ticket_emb_title,
                           description=ticket_emb_desc,
                           color=embed_color)


@bot.event
async def on_ready():
    log("Queue Bot is ready!", GREEN)
    bot.queuemsg = None
    check_tokens.start()
    update_queue.start()
    global currentstats
    currentstats = {}
    set_bot(bot)
  

#------------------ TASKS ------------------#
@tasks.loop(seconds=25)
async def update_queue():
    if queue_channel_id is None:
        return
    queuechnl = bot.get_channel(int(queue_channel_id))
    if queuechnl is queue_message_id:
        return

    if bot.queuemsg is None:
        bot.queuemsg = await queuechnl.fetch_message(int(queue_message_id))

    if bot.queuemsg is None:
        bot.queuemsg = await queuechnl.fetch_message(int(queue_message_id))

    embeds = bot.queuemsg.embeds
    embed = embeds[0]
    new_description = ""
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM queue ORDER BY position")
        rows = await cursor.fetchall()
        await cursor.close()
        total = 0
        for position, row in enumerate(rows, start=1):
            user = str(queuechnl.guild.get_member(int(row[0])))
            queue_emoji = green_queue_emoji if position == 1 else red_queue_emoji
            new_description += f"{position}. {queue_msg_desc.replace('QUEUE_EMOJI', queue_emoji).replace('USER', user).replace('AMOUNT', str(row[1]))}"
            total += int(row[1])
    embed.title = queue_msg_title        
    embed.description = new_description
    new_embed = discord.Embed(title=queue_msg_title, description=new_description)
    new_embed.set_footer(
        text=queue_msg_footer.replace("AMOUNT", str(len(rows))).replace("TOTAL", str(total))
    )
    await bot.queuemsg.edit(embed=new_embed)


@tasks.loop(minutes=30)
async def check_tokens():
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM queue ORDER BY position")
        rows = await cursor.fetchall()
        await cursor.close()
        if len(rows) == 0:
            return
        for row in rows:
            discord_id = row[0]
            token = row[2]
            headers = {
                'Authorization': token,
                'Content-type': 'application/json'
            }
            r = requests.get("https://discord.com/api/v9/users/@me",
                             headers=headers)
            if r.status_code == 401:
                if token == "invalid":
                    return
                else:
                    log(f"Invalid token: `{token}` Belongs to: {discord_id}")
                    await db.execute(
                        "UPDATE queue SET token = 'invalid' WHERE discord_id = ?",
                        (discord_id, ))
                    await db.commit()


@update_queue.before_loop
@check_tokens.before_loop
async def before_my_task():
    await bot.wait_until_ready()


#------------------ ON MESSAGE AND REMOVE CLAIM ------------------#
async def update_positions():
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute(
            "SELECT position FROM queue ORDER BY position")
        rows = await cursor.fetchall()
        await cursor.close()
        rows = [x[0] for x in rows]

        i = 0
        for row in rows:
            i += 1
            await db.execute(
                "UPDATE queue SET position = ? WHERE position = ?", (i, row))
            await db.commit()


async def removeclaim():
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM queue ORDER BY position")
        row = await cursor.fetchone()
        queue_amount = row[1]
        token = row[2]
        await cursor.close()
    if int(queue_amount) > 1:
        async with aiosqlite.connect("queue.db") as db:
            #print("queue_amount > 1")
            await db.execute(
                "UPDATE queue SET queue_amount = queue_amount -1 WHERE position = (SELECT min(position) FROM queue)"
            )
            #print("Executed")
            await db.commit()
            #print("Commited")
            #print("Closed DB")
    elif int(queue_amount) <= 1:
        async with aiosqlite.connect("queue.db") as db:
            #print("queue_amount <= 1")
            await db.execute(
                "DELETE FROM queue WHERE position = (SELECT min(position) FROM queue)"
            )
            #print("Executed")
            await db.commit()
            #print("Commited")
        await update_positions()
        #print("Updated Position")
        async with aiosqlite.connect("queue.db") as db:
            cursor = await db.execute("SELECT * FROM queue ORDER BY position")
            #print("SELECTED * FROM queue")
            row = await cursor.fetchone()
            #print("Fetched One")
            await cursor.close()
            #print("Closed Cursor")
            #print("Closed DB")
            token = row[2]
        update_token(token)
        #print("Updated Token")




async def snipes(type, delay):
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM queue")
        row = await cursor.fetchone()
        await cursor.close()
        discord_id = row[0]
        discordname = bot.get_user(discord_id)
        await db.execute(
            "INSERT INTO snipes (type, delay, discord_name) VALUES (?, ?,?)",
            (type, delay, discordname.name))
        await db.commit()


@bot.listen("on_message")
async def on_message(message):
    # Check if the message was sent in the channel specified by channel_id_sniped
    if message.channel.id != int(channel_id_sniped):
        return

    embeds = message.embeds
    if len(embeds) != 1:
        return
    embed = embeds[0]
    emb_dict = embed.to_dict()
    if message.author.bot and "title" in emb_dict and "Nitro Sniped" in emb_dict["title"]:
        delay = emb_dict["fields"][2]["value"]
        type = emb_dict["fields"][0]["value"]
        delay = delay.replace("`", "")
        type = type.replace("`", "")
        await removeclaim()
        await snipes(type, delay)
        channel = bot.get_channel(int(success_msg_channel))

        if ping_role == "":
            if "Classic" in type:
                text = success_msg_classic.replace("{type}", type).replace("{delay}", delay).replace("<@&{role}>", "")
            elif "Basic" in type:
                text = success_msg_basic.replace("{type}", type).replace("{delay}", delay).replace("<@&{role}>", "")
            else:
                text = success_msg_boost.replace("{type}", type).replace("{delay}", delay).replace("<@&{role}>", "")
        else:
            if "Classic" in type:
                text = success_msg_classic.replace("{type}", type).replace("{delay}", delay).replace("{role}", ping_role)
            elif "Basic" in type:
                text = success_msg_basic.replace("{type}", type).replace("{delay}", delay).replace("{role}", ping_role)
            else:
                text = success_msg_boost.replace("{type}", type).replace("{delay}", delay).replace("{role}", ping_role)

        if send_success_msg:
            if embed_success_msg:
                emb = discord.Embed(title=text,
                                    description=f"",
                                    color=embed_color)
                await channel.send(embed=emb)
            else:
                await channel.send(text)

        log(f"Nitro Sniped! | {type} in {delay}")



async def add_queue(member, amount, token):
    async with aiosqlite.connect("queue.db") as db:
        await db.execute(
            "INSERT INTO queue (discord_id, queue_amount, token, position) VALUES (?, ?, ?, (SELECT IFNULL(MAX(position) + 1, 1) FROM queue))",
            (member.id, amount, token))
        await db.commit()
        log(f"{member} has been added to the queue for {amount} claims!")
        await update_positions()


#------------------ COMMANDs ------------------#
#Add member to the database/queue

@bot.command()
@commands.has_permissions(administrator=True)
async def queue(ctx, member: discord.Member, amount, token):
    await ctx.message.delete()
    if not amount.isdigit():
        emb = discord.Embed(title=not_number_error_title,
                            description=not_number_error_description,
                            color=embed_color)
        await ctx.send(embed=emb)
        return
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM queue")
        rows = await cursor.fetchall()
        await cursor.close()
        if len(rows) == 0:
            await db.execute(
                "INSERT INTO queue (discord_id, queue_amount, token, position) VALUES (?, ?, ?, (SELECT IFNULL(MAX(position) + 1, 1) FROM queue))",
                (member.id, amount, token))
            await db.commit()
            update_token(token)
        else:
            await db.execute(
                "INSERT INTO queue (discord_id, queue_amount, token, position) VALUES (?, ?, ?, (SELECT IFNULL(MAX(position) + 1, 1) FROM queue))",
                (member.id, amount, token))
            await db.commit()
    log(f"{member} has been added to the queue for {amount} claims!")
    await update_positions()


@bot.command()
@commands.has_permissions(administrator=True)
async def move(ctx, pos1: int, pos2: int):
    async with aiosqlite.connect("queue.db") as db:
        await db.execute(
            "UPDATE queue SET position = case when position = ? then ? else ? end WHERE position in (?,?)",
            (pos1, pos2, pos1, pos1, pos2))
        await db.commit()

    await update_positions()
    if int(pos1) == 1 or (pos2) == 1:
        async with aiosqlite.connect("queue.db") as db:
            cursor = await db.execute("SELECT * FROM queue ORDER BY position")
            row = await cursor.fetchone()
            await cursor.close()
            token = row[2]
        log("First position moved, setting new main token")
        update_token(token)


#pulamea 


#Remove a person from the queue entirely
@bot.command()
@commands.has_permissions(administrator=True)
async def delete(ctx, member: discord.User):
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute(
            "SELECT * FROM queue WHERE discord_id = ? ORDER BY position",
            (member.id, ))
        rows = await cursor.fetchall()
        await cursor.close()
        if len(rows) == 1:
            cursor = await db.execute("SELECT * FROM queue ORDER BY position")
            row = await cursor.fetchall()
            await cursor.close()
            if row[0][0] != member.id:
                await db.execute("DELETE FROM queue WHERE discord_id = ?",
                                 (member.id, ))
                await db.commit()
                await update_positions()
                log(f"{member} has been removed from the queue!")
            else:
                await db.execute("DELETE FROM queue WHERE discord_id = ?",
                                 (member.id, ))
                await db.commit()
                await update_positions()
                cursor = await db.execute(
                    "SELECT * FROM queue ORDER BY position")
                row = await cursor.fetchone()
                await cursor.close()
                token = row[2]
                log("Removed first user from queue, setting new main token")
                update_token(token)
        elif len(rows) > 1:
            emb = discord.Embed(title="Which position do you want to delete?",
                                description=" ",
                                color=embed_color)
            for row in rows:
                if member.id in row:
                    emb.add_field(name=f"Position: {row[3]}",
                                  value=f"<@{row[0]}> : Claims: {row[1]}",
                                  inline=False)
            emb = await ctx.send(embed=emb)

            def check(m):
                return m.author.id == ctx.author.id

            msg = await bot.wait_for("message", check=check)
            pos = int(msg.content)

            await msg.delete()
            await emb.delete()

            await db.execute("DELETE FROM queue WHERE position = ?", (pos, ))
            await db.commit()
            await update_positions()

            if pos == 1:
                cursor = await db.execute(
                    "SELECT * FROM queue ORDER BY position")
                row = await cursor.fetchone()
                await cursor.close()
                token = row[2]
                log("Removed first user from queue, setting new main token")
                update_token(token)


#Replace members token in the database if its invalid
@bot.command()
@commands.has_permissions(administrator=True)
async def replacetoken(ctx, member: discord.Member, token):
    await ctx.message.delete()
    async with aiosqlite.connect("queue.db") as db:
        await db.execute("UPDATE queue SET token = ? WHERE discord_id = ?",
                         (token, member.id))
        await db.commit()
        emb = discord.Embed(title=f"{member}'s token has been replaced!",
                            description=" ",
                            colour=embed_color)
        await ctx.send(embed=emb)
        log(f"{member}'s token has been replaced!")
        cursor = await db.execute("SELECT * FROM queue ORDER BY position")
        row = await cursor.fetchone()
        await cursor.close()
        discord_id = row[0]
        token = row[2]
        if discord_id == member.id:
            update_token(token)
"""

#get every rdp ip from the database
async def get_vps():
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM vps")
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

#make a get request to every ip
async def get_stats():
    vps = await get_vps()
    for ip, user, passw in vps:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"http://{ip}:1243/stats")  
            
"""

#View all data in the database
@bot.command()
@commands.has_permissions(administrator=True)
async def viewdb(ctx):
    await ctx.message.delete()
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM queue ORDER BY position")
        rows = await cursor.fetchall()
        await cursor.close()
        if rows:
            people = []
            for row in rows:
                people.append(
                    f"**<@{row[0]}>**({row[0]}) | **{row[1]}** | **{row[2]}** | **{row[3]}**"
                )
            emb = discord.Embed(
                title="Database!",
                description="Member ID | Claims | Token | Position\n" +
                "\n".join(people),
                colour=embed_color)
            await ctx.send(embed=emb)
        else:
            await ctx.send("No members in queue")


#add x amount of claims to member in the queue
@bot.command()
@commands.has_permissions(administrator=True)
async def addclaims(ctx, member: discord.Member, amount):
    await ctx.message.delete()
    if not amount.isdigit():
        emb = discord.Embed(title="Amount must be a number!",
                            description=" ",
                            color=embed_color)
        await ctx.send(embed=emb)
        return

    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute(
            "SELECT * FROM queue WHERE discord_id = ? ORDER BY position",
            (member.id, ))
        rows = await cursor.fetchall()
        await cursor.close()
        if len(rows) == 1:
            await db.execute(
                "UPDATE queue SET queue_amount = queue_amount + ? WHERE discord_id = ?",
                (amount, member.id))
            await db.commit()
            log(f"{member}'s queue claims have been increased by {amount}!")
        elif len(rows) > 1:
            emb = discord.Embed(title="Which position do you want to use?",
                                description=" ",
                                color=embed_color)
            for row in rows:
                if member.id in row:
                    emb.add_field(name=f"Position: {row[3]}",
                                  value=f"<@{row[0]}> : Claims: {row[1]}",
                                  inline=False)
            emb = await ctx.send(embed=emb)

            def check(m):
                return m.author.id == ctx.author.id

            msg = await bot.wait_for("message", check=check)
            pos = int(msg.content)

            await msg.delete()
            await emb.delete()

            await db.execute(
                "UPDATE queue SET queue_amount = queue_amount + ? WHERE discord_id = ? AND position = ?",
                (amount, member.id, pos))
            await db.commit()
            log(f"{member}'s queue claims have been increased by {amount} for position {pos}!"
                )


#remove x amount of claims to member in the queue
@bot.command()
@commands.has_permissions(administrator=True)
async def removeclaims(ctx, member: discord.Member, amount):
    await ctx.message.delete()
    if not amount.isdigit():
        emb = discord.Embed(title="Amount must be a number!",
                            description=" ",
                            color=embed_color)
        await ctx.send(embed=emb)
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute(
            "SELECT * FROM queue WHERE discord_id = ? ORDER BY position",
            (member.id, ))
        rows = await cursor.fetchall()
        await cursor.close()
        if len(rows) == 1:
            cursor = await db.execute(
                "SELECT * FROM queue WHERE discord_id = ? ORDER BY position",
                (member.id, ))
            row = await cursor.fetchone()
            await cursor.close()
            if row is None:
                log("User is not in the queue!")
            queue_amount = row[1]
            if int(queue_amount) - int(amount) < 1:
                await db.execute("DELETE FROM queue WHERE discord_id = ?",
                                 (member.id, ))
                await db.commit()
                log(f"{member} has been deleted from the queue, user had 0 claims left!"
                    )
                await update_positions()
            else:
                await db.execute(
                    "UPDATE queue SET queue_amount = queue_amount - ? WHERE discord_id = ?",
                    (amount, member.id))
                await db.commit()
                log(f"{member}'s queue claims have been decreased by {amount}!"
                    )
        elif len(rows) > 1:
            emb = discord.Embed(title="Which position do you want to use?",
                                description=" ",
                                color=embed_color)
            for row in rows:
                if member.id in row:
                    emb.add_field(name=f"Position: {row[3]}",
                                  value=f"<@{row[0]}> : Claims: {row[1]}",
                                  inline=False)
            emb = await ctx.send(embed=emb)

            def check(m):
                return m.author.id == ctx.author.id

            msg = await bot.wait_for("message", check=check)
            pos = int(msg.content)

            await msg.delete()
            await emb.delete()

            cursor = await db.execute(
                "SELECT * FROM queue WHERE discord_id = ? AND position = ?",
                (member.id, pos))
            row = await cursor.fetchone()
            await cursor.close()
            queue_amount = row[1]
            if int(queue_amount) - int(amount) < 1:
                await db.execute(
                    "DELETE FROM queue WHERE discord_id = ? AND position = ?",
                    (member.id, pos))
                await db.commit()
                log(f"{member} has been deleted from the queue for position {pos}, user had 0 claims left!"
                    )
                await update_positions()
            else:
                await db.execute(
                    "UPDATE queue SET queue_amount = queue_amount - ? WHERE discord_id = ? AND position = ?",
                    (amount, member.id, pos))
                await db.commit()
                log(f"{member}'s queue claims have been decreased by {amount}! for position {pos}"
                    )


#force update Main token in vps in case of any issues
@bot.command()
@commands.has_permissions(administrator=True)
async def update(ctx):
    await ctx.message.delete()
    async with aiosqlite.connect("queue.db") as db:
        cursor = await db.execute("SELECT * FROM queue ORDER BY position")
        row = await cursor.fetchone()
        await cursor.close()
        token = row[2]
    update_token(token)
    log("Main token updated!")







@bot.command()
@commands.has_permissions(administrator=True)
async def help(ctx):    
    emb = discord.Embed(title=f"Commands", description=" ", colour=embed_color)
    emb.add_field(
        name="`queue <@member> <amount> <token>`",
        value="Adds a member to the queue for a certain amount of claims",
        inline=False)
    emb.add_field(name="`delete <@member>`",
                  value="Delete a member from the queue",
                  inline=False)
    emb.add_field(name="`move <pos1> <pos2>`",
                  value="Move positions in the queue",
                  inline=False)
    emb.add_field(name="`addvps <ip> <user> <pass>`",
                  value="Add a vps to the bot",
                  inline=False)
    emb.add_field(name="`deletevps <ip>`",
                  value="Remove a vps to the bot",
                  inline=False)
    emb.add_field(name="`addclaims <@member> <amount>`",
                  value="Adds a certain amount of claims to a member",
                  inline=False)
    emb.add_field(name="`removeclaims <@member> <amount>`",
                  value="Removes a certain amount of claims from a member",
                  inline=False)
    emb.add_field(name="`replacetoken <@member> <new_token>`",
                  value="Replace members token if its invalid",
                  inline=False)
    emb.add_field(name="`update`",
                  value="Refresh the main token inside of the vps",
                  inline=False)
    emb.add_field(name="`viewdb`",
                  value="Pulls all users from the database",
                  inline=False)
    emb.add_field(name="`restart`",
                  value="Restarts Tempo",
                  inline=False)
    emb.add_field(
        name="`queuemsg <title>`",
        value=
        "Sends an empty embed for the queue (will overwrite previous IDs in the database, leave title blank for default)",
        inline=False)
    emb.add_field(
        name="`ticketmsg`",
        value="Sends the embed for the ticket so users can react to it")
    emb.add_field(name="`-help`", value="Shows this message", inline=False)
    
    await ctx.send(embed=emb)


#restart tempo on vps
@bot.command()
@commands.has_permissions(administrator=True)
async def restart(ctx):
    restart_all_vps()
    log("Snipers has been restarted on all vps's!")


#Send empty embed which will be edited for the queue
@bot.command()
@commands.has_permissions(administrator=True)
async def queuemsg(ctx, title):
    await ctx.message.delete()
    if title is None:
        title = queue_msg_title
    embed = discord.Embed(title=title, description=" ", color=embed_color)
    embed.set_footer(text=f"Updates every 25 seconds.")
    emb = await ctx.send(embed=embed)
    #print("queuemsg", emb.id)
    async with aiosqlite.connect("queue.db") as db:
        await db.execute("UPDATE config SET value=? WHERE key=?",
                         (emb.id, "queue_message_id"))
        await db.execute("UPDATE config SET value=? WHERE key=?",
                         (ctx.channel.id, "queue_channel_id"))
        await db.commit()
    load_config()


@bot.command()
@commands.has_permissions(administrator=True)
async def addvps(ctx, ip, user, passw):
    async with aiosqlite.connect("queue.db") as db:
        await db.execute(
            "INSERT INTO vps (vps_ip, vps_user, vps_pass) VALUES (?, ?, ?)",
            (ip, user, passw))
        await db.commit()
        await ctx.send(f"{ip} added")
        log(f"{ip} added")


@bot.command()
@commands.has_permissions(administrator=True)
async def deletevps(ctx, ip):
    async with aiosqlite.connect("queue.db") as db:
        await db.execute("DELETE FROM vps WHERE vps_ip = ?", (ip, ))
        await db.commit()
        await ctx.send(f"{ip} delete")
        log(f"{ip} deleted")


@bot.event
async def on_raw_reaction_add(payload):
    payload_channel = bot.get_channel(payload.channel_id)

    if str(payload.emoji) == new_order_reaction:  # new-order channel
        message = await payload_channel.fetch_message(payload.message_id)
        reaction = message.reactions[0]

        async for user in reaction.users():
            if user.id != bot.user.id:
                member = message.guild.get_member(user.id)

                await reaction.remove(
                    user)  # Remove reaction of the user who clicked
                category = bot.get_channel(
                    int(ticket_category_id))  # ticket category

                overwrites = {
                    message.guild.default_role:
                    discord.PermissionOverwrite(read_messages=False),
                    member:
                    discord.PermissionOverwrite(read_messages=True)
                }

                channel = await category.create_text_channel(
                    f"ticket-{user.name}", overwrites=overwrites)

                embed = discord.Embed(color=embed_color)
                embed.add_field(name=new_ticket_manager_title,
                                value=new_ticket_manager_desc)

                message = await channel.send(embed=embed)
                await message.add_reaction("🗑️")

                embed = discord.Embed(color=embed_color)
                embed.add_field(
                    name=new_ticket_msg_title,
                    value=new_ticket_msg_desc.replace("MEMBER", member.mention)
                )

                await channel.send(embed=embed)

                async with channel.typing():
                    await asyncio.sleep(0.8)

                def check(msg):
                    return msg.author.id == member.id and msg.channel.id == channel.id

                while True:
                    embed = discord.Embed(
                        title=claims_ticket_title,
                        description=claims_ticket_desc,
                        color=embed_color)
                    await channel.send(embed=embed)
                    msg = await bot.wait_for('message', check=check)
                    try:
                        claims = int(msg.content)
                    except:
                        pass
                    else:
                        if claims > 0:
                            break

                method = ""

                if paypal_payments:
                    while True:
                        embed = discord.Embed(
                            title=payment_choice_title,
                            description=payment_choice_desc,
                            color=embed_color)
                        await channel.send(embed=embed)
                        msg = await bot.wait_for('message', check=check)
                        method = msg.content.upper()
                        if method in "CRYPTO":
                            method = "CRYPTO"
                            break
                        if method in "PAYPAL" or method in "PP":
                            method = "PAYPAL"
                            break

                if method == "CRYPTO" or not paypal_payments:
                    currencies = ["BTC", "ETH", "LTC", "DOGE", "DASH"]
                    formatted = " / ".join(currencies)

                    while True:
                        embed = discord.Embed(
                            title=claims_ticket_cryptos.replace("CRYPTOS", formatted),
                            color=embed_color)
                        await channel.send(embed=embed)
                        msg = await bot.wait_for('message', check=check)
                        currency = msg.content.upper()
                        if currency in currencies:
                            break

                    currency_price = httpx.get(
                        "https://pricing.a.exodus.io/current-price?from=BTC,ETH,LTC,DOGE,DASH&to=USD&ignoreInvalidSymbols=true"
                    ).json()[currency]["USD"]
                    amount = (claims * float(claim_price)) / currency_price
                    amount = round(amount, 8)
                    display_amount = '{:f}'.format(amount)

                    async with aiosqlite.connect("queue.db") as db:
                        cursor = await db.execute(
                            "SELECT address FROM crypto WHERE symbol = ?",
                            (currency, ))
                        row = await cursor.fetchone()
                        await cursor.close()
                    address = row[0]
                    embed = discord.Embed(color=embed_color)
                    embed.add_field(
                        name=payment_msg_title,
                        value=payment_msg_desc.replace("DISPLAY_AMOUNT", display_amount).replace("CURRENCY", currency).replace("ADDRESS", address)
                    )
                    await channel.send(embed=embed)

                    txids = open("txids.txt", "r").read().splitlines()
                    txs = get_txids(address, currency)

                    for i in txs:
                        txid = i[0]
                        if txid not in txids:
                            open("txids.txt", "a").write(txid + "\n")

                    txids = open("txids.txt", "r").read().splitlines()
                    txid = None

                    while True:
                        embed = discord.Embed(color=embed_color)
                        embed.add_field(
                            name=txid_title,
                            value=txid_desc
                        )
                        await channel.send(embed=embed)

                        msg = await bot.wait_for('message', check=check)
                        txid = msg.content

                        if txid in txids:
                            embed = discord.Embed(color=error_color,
                                                  title=f"**TXID Already Used!**")
                            await channel.send(embed=embed)
                        else:
                            txs = get_txids(address, currency)
                            is_good = False
                            for i in txs:
                                if i[0] == txid:
                                    if i[1] >= amount:
                                        is_good = True
                                        break
                                    else:
                                        embed = discord.Embed(color=error_color)
                                        embed.add_field(
                                            name=f"**Unsufficient Amount!**",
                                            value=
                                            f"Please talk with a Staff Member.")
                                        await channel.send(embed=embed)
                            if is_good:
                                break

                    embed = discord.Embed(color=embed_color)
                    embed.add_field(name=f"**Transaction Received!** ✅",
                                    value=f"Let's wait for 3 confirmations...")
                    await channel.send(embed=embed)

                    open("txids.txt", "a").write(txid + "\n")

                    while True:
                        await asyncio.sleep(25)
                        if get_confirmations(txid, currency) >= 3:
                            break

                    log(f"Received {amount} {currency}.")
                if method == "PAYPAL":
                    amount = claims * float(claim_price)
                    embed = discord.Embed(
                        title=send_paypal_title,
                        description=send_paypal_desc.replace("DISPLAY_AMOUNT", amount).replace("ADDRESS", paypal_address),
                        color=embed_color)
                    await channel.send(embed=embed)
                    msg = await bot.wait_for('message', check=check)
                    client_email = msg.content.upper()
                    payment = get_parent_map(paypal_address, paypal_password, client_email)
                    if payment is not None:
                        log(f"Received {payment} USD.")
                        if payment >= amount:
                            embed = discord.Embed(color=embed_color)
                            embed.add_field(name=f"**Transaction Received!** ✅",
                                            value=f"Thanks for your purchase...")
                            await channel.send(embed=embed)
                        else:
                            embed = discord.Embed(color=error_color)
                            embed.add_field(
                                name=f"**Unsufficient Amount!**",
                                value=f"Please talk with a Staff Member.")
                            await channel.send(embed=embed)
                            return



                member_token = None

                while True:
                    embed = discord.Embed(color=embed_color)
                    embed.add_field(
                        name=send_token_title,
                        value=send_token_desc
                    )
                    await channel.send(embed=embed)

                    msg = await bot.wait_for('message', check=check)
                    member_token = msg.content

                    headers = {
                        "Authorization": member_token,
                        "Content-Type": "application/json"
                    }

                    requests_user = requests.get(
                        'https://discord.com/api/v9/users/@me',
                        headers=headers)

                    if requests_user.status_code == 200:
                        break
                    else:
                        embed = discord.Embed(color=error_color)
                        embed.add_field(name=f"**Invalid Token!**",
                                        value=f"Please try again.")
                        await channel.send(embed=embed)

                await add_queue(member, claims, member_token)

                embed = discord.Embed(color=embed_color)
                embed.add_field(name=f"**You have been added to the queue!**",
                                value=f"You will receive {claims} claims.")

                await channel.send(embed=embed)

                date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                if method == "CRYPTO" or not paypal_payments:
                    async with aiosqlite.connect("queue.db") as db:
                        await db.execute(
                            "INSERT INTO payments (txid, symbol, amount, sender, time) VALUES (?, ?, ?, ?, ?)",
                            (txid, currency, amount, member.id, date))
                        await db.commit()
                if method == "PAYPAL":
                    async with aiosqlite.connect("queue.db") as db:
                        await db.execute(
                            "INSERT INTO payments (txid, symbol, amount, sender, time) VALUES (?, ?, ?, ?, ?)",
                            (client_email, "PP", amount, member.id, date))
                        await db.commit()

    elif "ticket-" in payload_channel.name and payload.emoji.name == "🗑️" and payload.user_id != bot.user.id:
        channel = payload_channel

        css = '''
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300&display=swap');

body {
background-color: #6b5c9c;
color: #dcddde;
font-family: 'Roboto', sans-serif;
}
a {
color: #0096cf;
}
.info {
display: flex;
max-width: 100%;
margin: 0 5px 10px;
}
.guild-icon-container {
flex: 0;
}
.guild-icon {
max-width: 88px;
max-height: 88px;
}
.metadata {
flex: 1;
margin-left: 10px;
}
.guild-name {
font-size: 1.4em;
}
.channel-name {
font-size: 1.2em;
}
.channel-topic {
margin-top: 2px;
}
.channel-message-count {
margin-top: 2px;
}
.chatlog {
max-width: 100%;
margin-bottom: 24px;
}
.message-group {
display: flex;
margin: 0 10px;
padding: 15px 0;
}
.author-avatar-container {
flex: 0;
width: 40px;
height: 40px;
}
.author-avatar {
border-radius: 50%;
height: 40px;
width: 40px;
}
.messages {
flex: 1;
min-width: 50%;
margin-left: 20px;
}
.author-name {
font-size: 1em;
font-weight: 900;
}
.timestamp {
margin-left: 5px;
font-size: 0.75em;
}
.message {
padding: 2px 5px;
margin-right: -5px;
margin-left: -5px;
background-color: transparent;
transition: background-color 1s ease;
}
.content {
font-size: 0.9375em;
word-wrap: break-word;
}
.mention {
color: #7289da;
}
                '''

        def check_message_mention(msgs: discord.Message):
            user_mentions: list = msgs.mentions
            role_mentions: list = msgs.role_mentions
            channel_mentions: list = msgs.channel_mentions
            total_mentions: list = user_mentions + role_mentions + channel_mentions
            m: str = msgs.content
            for mentions in total_mentions:
                if mentions in user_mentions:
                    for mention in user_mentions:
                        m = m.replace(
                            str(f"<@{mention.id}>"),
                            f"<span class=\"mention\">@{mention.name}</span>")
                        m = m.replace(
                            str(f"<@!{mention.id}>"),
                            f"<span class=\"mention\">@{mention.name}</span>")
                elif mentions in role_mentions:
                    for mention in role_mentions:
                        m = m.replace(
                            str(f"<@&{mention.id}>"),
                            f"<span class=\"mention\">@{mention.name}</span>")
                elif mentions in channel_mentions:
                    for mention in channel_mentions:
                        m = m.replace(
                            str(f"<#{mention.id}>"),
                            f"<span class=\"mention\">#{mention.name}</span>")
                else:
                    pass
            return m

        messages: discord.TextChannel.history = [
            message
            async for message in channel.history(limit=None, oldest_first=True)
        ]

        f = f'''
<!DOCTYPE html>
<html>

<head>
<meta charset=utf-8>
<meta name=viewport content="width=device-width">
<style>
{css}
</style>
</head>

<body>
<div class=info>
<div class=metadata>
<div class=guild-name>{channel.guild.name}</div>
<div class=channel-name>#{channel.name}</div>
<div class=channel-message-count>{len(messages)} messages</div>
</div>
</div>
            '''

        for message in messages:
            if message.embeds:
                content = 'Embed'
            elif message.attachments:
                if message.attachments[0].url.endswith(
                    ('jpg', 'png', 'gif', 'bmp')):
                    if message.content:
                        content = check_message_mention(
                            message
                        ) + '<br>' + f"<img src=\"{message.attachments[0].url}\" width=\"200\" alt=\"Attachment\" \\>"
                    else:
                        content = f"<img src=\"{message.attachments[0].url}\" width=\"200\" alt=\"Attachment\" \\>"
                elif message.attachments[0].url.endswith(
                    ('mp4', 'ogg', 'flv', 'mov', 'avi')):
                    if message.content:
                        content = check_message_mention(
                            message) + '<br>' + f'''
                        <video width="320" height="240" controls>
                          <source src="{message.attachments[0].url}" type="video/{message.attachments[0].url[-3:]}">
                        Your browser does not support the video.
                        </video>
                        '''
                    else:
                        content = f'''
                        <video width="320" height="240" controls>
                          <source src="{message.attachments[0].url}" type="video/{message.attachments[0].url[-3:]}">
                        Your browser does not support the video.
                        </video>
                        '''
                elif message.attachments[0].url.endswith(('mp3', 'boh')):
                    if message.content:
                        content = check_message_mention(
                            message) + '<br>' + f'''
                        <audio controls>
                          <source src="{message.attachments[0].url}" type="audio/{message.attachments[0].url[-3:]}">
                        Your browser does not support the audio element.
                        </audio>
                        '''
                    else:
                        content = f'''
                        <audio controls>
                          <source src="{message.attachments[0].url}" type="audio/{message.attachments[0].url[-3:]}">
                        Your browser does not support the audio element.
                        </audio>
                        '''
                else:
                    pass
            else:
                content = check_message_mention(message)

            f += f'''
            <div class="message-group">
                <div class="author-avatar-container"><img class=author-avatar src={message.author.avatar_url}></div>
                <div class="messages">
                    <span class="author-name" >{message.author.name}</span><span class="timestamp">{message.created_at.strftime("%b %d, %Y %H:%M")}</span>
                    <div class="message">
                        <div class="content"><span class="markdown">{content}</span></div>
                    </div>
                </div>
            </div>
            '''
        f += '''
                </div>
            </body>
        </html>
        '''

        transcripts = bot.get_channel(
            int(transcript_channel_id))  # transcripts
        await transcripts.send(
            f"**Channel '#{channel.name}' has been deleted!**\nChannel Transcript",
            file=discord.File(fp=io.StringIO(f), filename='transcript.html'))

        await payload_channel.delete()


@bot.command()
@commands.has_permissions(administrator=True)
async def ticketmsg(ctx):
    msg = await ctx.send(embed=ticket_emb)
    await msg.add_reaction(new_order_reaction)


@bot.command()
async def stats(ctx):
    # check if 10 minutes have passed since last update
    print("Updating stats...")
    currentstats = getstats()
    print(currentstats)
    currentstats['time'] = datetime.now()
    print(1)
    e = discord.Embed(title=f"Stats (Last Updated: <t:{currentstats['time']}:R>)")
    print(2)
    e.add_field(name='Total Servers',value=currentstats['total_servers'])
    print(3)
    e.add_field(name='Total Alts',value=currentstats['alts'])
    print(4)
    await ctx.send(embed=e)


#error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        emb = discord.Embed(title="Missing Required Argument(s)!",
                            description="Do `-help` for all commands",
                            color=embed_color)
        await ctx.send(embed=emb)
        return
    elif isinstance(error, commands.BadArgument):
        emb = discord.Embed(title="You have provided an invalid argument!",
                            description="Do `-help` for all commands",
                            color=embed_color)
        await ctx.send(embed=emb)
        return


def start(func):
    global set_bot
    set_bot = func
    file = open("bot_token.txt", "r")
    token = file.readline()
    bot.run(token)
