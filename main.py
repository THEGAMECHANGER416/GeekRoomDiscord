import os, disnake, random, re
import disnake.ext
from disnake.ext import tasks
from disnake.ext import commands
from dotenv import load_dotenv
from datetime import datetime,timedelta
import riddle_of_theday
import links 


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
print(TOKEN)
 
intents = disnake.Intents.default()
intents.message_content = True

Bot = commands.Bot(
    command_prefix=disnake.ext.commands.when_mentioned,
    activity=disnake.Activity(type=disnake.ActivityType.watching, name="Geek Room The Anime"),
    intents=intents
)

#ID of channel where questions are posted
qotdtarget = int(os.getenv('QOTD_TARGET'))#1116378200096907264#fill in  #varxqotd 
riddlechannel = int(os.getenv('RIDDLECHANNEL'))
#ID of role that gets pinged when posting a question, leave blank string if no role should be pinged
pingrole = os.getenv('PINGROLE') #Member role ID for @DSA  #varxmember
memechannel = int(os.getenv('MEMECHANNEL'))

#Hour QOTD is to be posted
posttime = int(os.getenv('POSTTIME'))
ADMIN_ROLE_NAME  = ["Moderator","admin","core","GOD","coordinator"]
embedcolor = disnake.Colour.green() 
errorembedcolor = disnake.Colour.red()

#Scraping questions from leetecode
import requests
from bs4 import BeautifulSoup
import random
import re
from disnake import utils

async def question_post(channel):
    #Scraping questions from leetecode
    # Send a GET request to the website
    r = requests.get('https://bishalsarang.github.io/Leetcode-Questions/out.html')

    # Parse the HTML content
    soup = BeautifulSoup(r.content, "html.parser")

    # Find all question titles and descriptions
    questions = soup.find_all("div", class_="content__u3I1 question-content__JfgR")

    # Select a random question
    random_question = random.choice(questions)

    # Extract question title with regex
    title = random_question.find_previous_sibling("div", id="title").text.strip()
    title = re.sub(r'^\d+.','',title)

    # Extract question description and remove problematic Unicode characters
    description = random_question.find("div").text.strip()
    description_cleaned = description.replace('\u230a', '')  # Replace problematic Unicode character
    #Prettify the text
    description_cleaned = await riddle_of_theday.generate_response_with_text("Prettify the following description to be sent in a discord embed : " + description_cleaned)
    
    # Construct the problem link
    title_with_hyphens = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-').lower()
    link_without_number = re.sub(r'^\d+-', '', title_with_hyphens)
    link_without_number = "https://leetcode.com/problems/"+link_without_number

    # Create an embed with the title, description, and link
    embed = disnake.Embed(
        title=title,
        description=description_cleaned,
        colour=embedcolor
    )
    embed.add_field(name="Problem Link", value=f"[Click here]({link_without_number})")
    embed.set_author(name="Today's problem:", 
                     icon_url='https://images.playground.com/85f17db5dc3a4b38acc26419711b6c4d.jpeg')#replace with any other/bot icon
    embed.set_footer(text=f"Daily Question #{datetime.now().date()}")

    # Send the embed to the channel
    guild = channel.guild  # Get the guild (server) of the channel
    riddles_role = utils.get(guild.roles, name=pingrole)
    if pingrole == "":
        await channel.send(embed=embed)
    else:
        await channel.send(f"<@&{riddles_role.id}>", embed=embed)
    message = channel.last_message
    await message.create_thread(
        name=f"'{title}'",
        auto_archive_duration=60)

    print(f'{Bot.user} has posted a qotd!')


last_posted_date = None
#Scheduled to call question of the day.
def postmeme(channel):
    try:
        response = requests.get("https://meme-api.com/gimme/ProgrammerHumor")
        data = response.json()
        
        
        title = data['title']
        image_url = data['url']
        
        
        embed = disnake.Embed(title=title, color=disnake.Color.blue())
        embed.set_image(url=image_url)
        
        
        return embed

    except Exception as e:
        print(e)
        return "Failed to fetch meme. Please try again later."

@tasks.loop(hours = 1)
async def task():
    global last_posted_date
    current_date = datetime.now().date()
    if datetime.now().hour == posttime and last_posted_date!=current_date:
        channel = Bot.get_channel(qotdtarget)
        await question_post(channel) #daily DSA
        last_posted_date = current_date
        channel = Bot.get_channel(memechannel)
        await channel.send(embed=postmeme(channel))

        topicdict = {'Artificial Intelligence & Machine Learning':os.getenv('AICHANNEL'),
                     'Cybersecurity':os.getenv('CYBCHANNEL'),
                     'Robotics & IOT':os.getenv('IOTCHANNEL'),
                     'DSA, Problem Solving and Aptitute':riddlechannel,
                     'Web Development':os.getenv('WEBDEVCHANNEL')}
        for topic,channel in topicdict.items():
            await riddle_of_theday.question_post(Bot.get_channel(int(channel)),topic) #Riddle post
        #question_post function posts DSA, whereas riddle_of_theday.question_post posts riddles            

#Make sure bot is online.
@Bot.event
async def on_ready():
    print(f'{Bot.user} has connected to Discord! It is '+ str(datetime.now()))
    await task.start()
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#Reads for commands, which includes adding questions and testing

#Enforcing command usage in bot-commands, bypass for admins
def isallowed(inter):
    channel = inter.channel
    member = inter.user
    has_bypass_permission = any(role.name in ADMIN_ROLE_NAME for role in member.roles)
    is_bot_commands_channel = channel.name == 'bot-commands'

    # If the member does not have admin/moderator roles and is not in #bot-commands, deny access
    if not has_bypass_permission and not is_bot_commands_channel:
        return False
    return True

usagewarn = "You cannot use this command outside the #bot-commands channel"
        

@Bot.slash_command(name="qotd", description="Sends daily QOTD, admin only")
@commands.has_permissions(administrator=True)
async def send(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer()
   
    try:
        channel = Bot.get_channel(qotdtarget)
        if channel is None :
            raise ValueError(f"Channel with ID{qotdtarget} not found")
        await question_post(channel)
        
        embed = disnake.Embed(
            title = f"Success!",
            description = f"Sent a QOTD.",
            colour = embedcolor,
        )
        await inter.edit_original_message(embed=embed)
    except Exception as e:
        # Handle any errors and respond appropriately
        error_embed = disnake.Embed(
            title="Error!",
            description=f"An error occurred: {str(e)}",
            color=0xff0000,
        )
        await inter.edit_original_response(embed=error_embed)

#riddle posting
@Bot.slash_command(name="riddle", description="Sends a riddle on a topic")
async def send(inter: disnake.ApplicationCommandInteraction,subject):
    
    if (not isallowed(inter)):
        await inter.send(usagewarn,ephemeral=True)
        return
    await inter.response.defer()
    try:
        channel = inter.channel
        if channel is None:
            raise ValueError(f"Channel  not found")

        # Assume riddle_of_theday.question_post(channel) is a function that posts the riddle
        await riddle_of_theday.question_post(channel,subject,False)

        embed = disnake.Embed(
            title="Success!",
            description="Sent a riddle",
            color=embedcolor,
        )
        
        await inter.edit_original_response(embed=embed)
    except Exception as e:
        # Handle any errors and respond appropriately
        error_embed = disnake.Embed(
            title="Error!",
            description=f"An error occurred: {str(e)}",
            color=0xff0000,
        )
        await inter.edit_original_response(embed=error_embed)

#==================================================================================================Links=======================================================================================
#reduce redundancy with global_options
global_options = links.global_options
from links import handle_insta,handle_twitter,handle_whatsapp,handle_discord,handle_nas,handle_linkedin,handle_linktree,handle_github
# Event listener for select menu interactions
@Bot.event
async def on_dropdown(inter: disnake.MessageInteraction):
    if inter.data.custom_id == "Bot-linkspanel":
        # Get the selected value from the interaction
        value = inter.values[0]
        
        # Call the appropriate handler function based on the selected value
        if value == "twitter-linkspanel":
            await handle_twitter(inter)
        elif value == "insta-linkspanel":
            await handle_insta(inter)
        elif value == "whatsapp-linkspanel":
            await handle_whatsapp(inter)
        elif value == "discord-linkspanel":
            await handle_discord(inter)
        elif value == "github-linkspanel":
            await handle_github(inter)
        elif value == "nasio-linkspanel":
            await handle_nas(inter)
        elif value == "linkedin-linkspanel":
            await handle_linkedin(inter)
        elif value == "linktree-linkspanel":
            await handle_linktree(inter)


@Bot.slash_command(name="links", description="Get links to the Geek Room community")
async def links(inter: disnake.ApplicationCommandInteraction):
    # Create the select menu options
    options = global_options

    # Create the select menu
    select_menu = disnake.ui.Select(
        placeholder="❌┆Links",
        options=options,
        custom_id="Bot-linkspanel"
    )

    # Create an action row with the select menu
    action_row = disnake.ui.ActionRow(select_menu)

    # Create the embed
    embed = disnake.Embed(
        title="🔗・Links",
        description="Get access to all Geek Room rescources from the menu!\nLinktree:",
        color=0x3498db
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/843487478881976381/874694194474668052/Bot_banner_invite.jpg")

    # Send the response with the embed and action row
    await inter.response.send_message(embed=embed, components=[action_row])

@Bot.slash_command(name="say", description="Send a message in a channel, (admin only)")
@commands.has_permissions(administrator=True)  # Require admin permissions
async def say(inter: disnake.ApplicationCommandInteraction, channel_id , message: str):
    channel = Bot.get_channel(channel_id)
    
    # Check if the channel exists
    if channel is None:
        embed = disnake.Embed(
            title="Error!",
            description="The specified channel does not exist.",
            color=0xff0000,
        )
        return await inter.send(embed=embed)
    
    # Send the message to the specified channel
    await channel.send(message)
    
    embed = disnake.Embed(
        title="Success!",
        description=f"Sent the message in {channel.mention}.",
        color=embedcolor,
    )
    await inter.send(embed=embed)

# Error handling for users without permissions
@say.error
async def say_error(inter: disnake.ApplicationCommandInteraction, error):
    if isinstance(error, commands.MissingPermissions):
        embed = disnake.Embed(
            title="Permission Denied!",
            description="You do not have permission to use this command.",
            color=0xff0000,
        )
        await inter.send(embed=embed)

@Bot.slash_command(name="summarise", description="Summarise chat upto a week - admin only")
@commands.has_permissions(administrator=True) 
async def summarise(inter, channel_id):
    await inter.response.defer()  # Defer the interaction first
    
    channel = Bot.get_channel(int(channel_id))
    
    # Calculate the start and end dates for the week
    end_date = datetime.now()  # Current local date and time
    start_date = end_date - timedelta(days=7)  # 7 days ago
    last_week = True
    summary = ''
    # Fetch messages within the week
    async for message in channel.history(limit=None, after=start_date, before=end_date):
            print(message.content)
            summary += f"{message.author.name}:{message.content}\n"
    
    if not summary:
        last_week = False
        print("No messages in the last 7 days, fetching the last 20 messages.")
        summary = ''  # Reset summary
        async for message in channel.history(limit=20):  # Limit set to 20
            print(message.content)
            summary += f"{message.author.name}: {message.content}\n"
    
    await riddle_of_theday.summarise(inter.channel,summary)
    embed = disnake.Embed(
        title = f"Success!",
        description = f"Summarised text for the time period {start_date} to {end_date}" if last_week else f"Summarised the last 20 messages",
        colour = embedcolor,
    )
    await inter.send(embed = embed)
@summarise.error
async def say_error(inter: disnake.ApplicationCommandInteraction, error):
    if isinstance(error, commands.MissingPermissions):
        embed = disnake.Embed(
            title="Permission Denied!",
            description="This command is admin-only.",
            color=0xff0000,
        )
        await inter.send(embed=embed)

def is_invite_link(content):
    return "discord.gg" in content or "discord.com/invite" in content

@Bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if is_invite_link(message.content):
        admin_role = disnake.utils.get(message.guild.roles, name=ADMIN_ROLE_NAME)
        print(message.author.roles)
        print(admin_role)
        if admin_role in message.author.roles:
            print("Link sent by admin")
        else:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, invite links are not allowed. Please refrain from posting them.")
    
    # Ensure commands still work
    await Bot.process_commands(message)

@Bot.slash_command(name="ping", description="Get ping in ms")
async def ping(inter:disnake.ApplicationCommandInteraction):
    if (not isallowed(inter)):
        await inter.send(usagewarn,ephemeral=True)
        return
    await inter.response.defer()
    latency = round(Bot.latency * 1000)  # Convert latency to milliseconds
    await inter.send(f"Pong! 🏓 {latency}ms")

#Meme    
@Bot.slash_command(name="meme",description="Programming humour")
async def meme(inter:disnake.ApplicationCommandInteraction):
    await inter.response.defer()
    channel = inter.channel
    member = inter.user
    has_bypass_permission = any(role.name in ADMIN_ROLE_NAME for role in member.roles)
    is_bot_commands_channel = channel.name == 'memes'
 
    if not has_bypass_permission and not is_bot_commands_channel:
        await inter.send("You cannot use this command outside of #memes",ephemeral=True)
        return 
    
    embed = postmeme(inter.channel)
     
    await inter.send(embed=embed)

@Bot.slash_command(name="ques",description="Test yourself on a topic, any question ")
async def ques(ctx:disnake.ApplicationCommandInteraction,topic):
    if (not isallowed(ctx)):
        await ctx.send(usagewarn,ephemeral=True)
        return
    ctx.response.defer()
    promt = "send me a " + topic + " question to solve"
  
    text = await riddle_of_theday.generate_response_with_text(promt)
    messages = []
    
    
    for i in range(0, len(text), 1700):
      sub_message = text[i:i + 1700]
      messages.append(sub_message)

    # Send each part as a separate message
    for string in messages:
      await ctx.channel.send(string)



    
Bot.run(TOKEN)


#==========================================================================================================Embed Linkspanel alternative======================================================================================
# @Bot.slash_command(name="link", description="Sends the Geek Room links")
# async def link(inter: disnake.ApplicationCommandInteraction):
#     await inter.response.defer()

#     try:
#         # Create an embed with the link
#         embed = disnake.Embed(
#             title="Links",
#             description="Here are the links to Geek Room's resources",
#             color=0x3498db
#         )
#         embed.add_field(
#             name="Linktree",
#             value="[Geek Room Linktree](https://linktr.ee/geekroom)",
#             inline=False
#         )
#         embed.add_field(
#             name="LinkedIn",
#             value="[Official LinkedIn Page](https://www.linkedin.com/company/geekr00m/)",
#             inline=False
#         )
#         embed.add_field(
#             name="Instagram",
#             value="[Official Instagram Page](https://www.instagram.com/geekr00m/)",
#             inline=False
#         )
#         embed.add_field(
#             name="Twitter",
#             value="[Geek Room Twitter](https://twitter.com/geek__room_)",
#             inline=False
#         )
#         embed.add_field(
#             name="Whatsapp Group",
#             value="[Geek Room Whatsapp](https://chat.whatsapp.com/EPDLVRHU1AM1HQ76NFWIDW)",
#             inline=False
#         )
#         embed.add_field(
#             name="Discord",
#             value="[Official Discord](https://discord.com/invite/7TEVm4pmMv)",
#             inline=False
#         )
#         embed.set_author(name=f"@geekroom",icon_url="https://ugc.production.linktr.ee/2a6c8d7a-a38a-45c4-9e9f-4a14b6c88714_GR-Logo.png?io=true&size=avatar-v3_0")
#         # embed.set_image(url="https://ugc.production.linktr.ee/2a6c8d7a-a38a-45c4-9e9f-4a14b6c88714_GR-Logo.png?io=true&size=avatar-v3_0")
#         embed.set_footer(text="Visit Geek Room for more awesome content!")

#         # Send the embed
#         await inter.edit_original_response(embed=embed)
#     except Exception as e:
#         # Handle any errors and respond appropriately
#         error_embed = disnake.Embed(
#             title="Error!",
#             description=f"An error occurred: {str(e)}",
#             color=0xff0000,
#         )
#         await inter.edit_original_response(embed=error_embed)

#=================================================================================================================================================================================================
