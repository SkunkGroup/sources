import datetime
import json
from typing import Union

import discord
import humanfriendly
from bot.bot import Evict
from bot.helpers import EvictContext
from bot.managers.emojis import Colors, Emojis
from cogs.config import InvokeClass
from discord.ext import commands
from patches.classes import Mod
from patches.permissions import GoodRole, Permissions


class ValidTime(commands.Converter):
    async def convert(self, ctx: EvictContext, argument: int):
        try:
            time = humanfriendly.parse_timespan(argument)
        except humanfriendly.InvalidTimespan:
            raise commands.BadArgument(f"**{argument}** is an invalid timespan")

        return time


class ClearMod(discord.ui.View):
    def __init__(self, ctx: EvictContext):
        super().__init__()
        self.ctx = ctx
        self.status = False

    @discord.ui.button(emoji=Emojis.approve)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.ctx.author.id:
            return await interaction.client.ext.warning(
                interaction, "You are not the author of this embed"
            )

        check = await interaction.client.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", interaction.guild.id
        )

        channelid = check["channel_id"]
        roleid = check["role_id"]
        logsid = check["jail_id"]

        channel = interaction.guild.get_channel(channelid)
        role = interaction.guild.get_role(roleid)
        logs = interaction.guild.get_channel(logsid)

        try:
            await channel.delete()
        except:
            pass
        try:
            await role.delete()
        except:
            pass
        try:
            await logs.delete()
        except:
            pass

        await interaction.client.db.execute(
            "DELETE FROM mod WHERE guild_id = $1", interaction.guild.id
        )

        self.status = True

        return await interaction.response.edit_message(
            view=None,
            embed=discord.Embed(
                color=Colors.color,
                description=f"> {Emojis.approve} {interaction.user.mention}: I have **disabled** moderation.",
            ),
        )

    @discord.ui.button(emoji=Emojis.deny)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.client.ext.warning(
                interaction, "You are not the author of this embed"
            )
        await interaction.response.edit_message(
            embed=discord.Embed(color=Colors.color, description="aborting action"),
            view=None,
        )
        self.status = True

    async def on_timeout(self) -> None:
        if self.status == False:
            for item in self.children:
                item.disabled = True

            await self.message.edit(view=self)


class ModConfig:

    async def sendlogs(
        bot: commands.Bot,
        action: str,
        author: discord.Member,
        victim: Union[discord.Member, discord.User],
        reason: str,
    ):
        check = await bot.db.fetchrow(
            "SELECT channel_id FROM mod WHERE guild_id = $1", author.guild.id
        )
        if check:
            res = await bot.db.fetchrow(
                "SELECT count FROM cases WHERE guild_id = $1", author.guild.id
            )
            case = int(res["count"]) + 1
            await bot.db.execute(
                "UPDATE cases SET count = $1 WHERE guild_id = $2", case, author.guild.id
            )
            embed = discord.Embed(color=Colors.color, timestamp=datetime.datetime.now())
            embed.set_author(name="Modlog Entry", icon_url=author.display_avatar)
            embed.add_field(
                name="Information",
                value=f"**Case #{case}** | {action}\n**User**: {victim} (`{victim.id}`)\n**Moderator**: {author} (`{author.id}`)\n**Reason**: {reason}",
            )
            try:
                await author.guild.get_channel(int(check["channel_id"])).send(
                    embed=embed
                )
            except:
                pass


class moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @Mod.is_mod_configured()
    @commands.command(
        description="disable the moderation features in your server",
        brief="administrator",
    )
    @Permissions.has_permission(administrator=True)
    async def unsetmod(self, ctx: EvictContext):

        check = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
        )

        if not check:
            return await ctx.warning("Moderation is **not** enabled in this server.")

        view = ClearMod(ctx)
        view.message = await ctx.reply(
            view=view,
            embed=discord.Embed(
                color=Colors.color,
                description=f"> {ctx.author.mention} Are you sure you want to disable moderation?",
            ),
        )

    @commands.command(
        description="enable the moderation features in your server",
        brief="administrator",
    )
    @Permissions.has_permission(administrator=True)
    async def setmod(self, ctx: EvictContext):

        check = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
        )

        if check:
            return await ctx.warning("Moderation is **already** enabled in this server")

        await ctx.typing()

        role = await ctx.guild.create_role(name="evict-jail")

        for channel in ctx.guild.channels:
            await channel.set_permissions(role, view_channel=False)

        overwrite = {
            role: discord.PermissionOverwrite(view_channel=True),
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }

        over = {ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)}

        category = await ctx.guild.create_category(name="evict mod", overwrites=over)

        text = await ctx.guild.create_text_channel(
            name="mod-logs", overwrites=over, category=category
        )
        jai = await ctx.guild.create_text_channel(
            name="jail", overwrites=overwrite, category=category
        )

        await self.bot.db.execute(
            "INSERT INTO mod VALUES ($1,$2,$3,$4)",
            ctx.guild.id,
            text.id,
            jai.id,
            role.id,
        )

        await self.bot.db.execute("INSERT INTO cases VALUES ($1,$2)", ctx.guild.id, 0)
        return await ctx.success("I have **enabled** moderation.")

    @commands.command(description="clone a channel", brief="manage channels")
    @Permissions.has_permission(manage_channels=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def nuke(self, ctx: EvictContext, channel: discord.TextChannel = None):

        embed = discord.Embed(
            color=Colors.color, description=f"Do you want to **nuke** this channel?"
        )

        yes = discord.ui.Button(emoji=Emojis.approve)

        no = discord.ui.Button(emoji=Emojis.deny)

        guild = ctx.guild

        if not channel:
            channel: discord.TextChannel = ctx.channel

        async def yes_callback(interaction: discord.Interaction):

            if not interaction.user:
                return await self.bot.ext.warning(
                    interaction,
                    "You are not the **author** of this embed",
                    ephemeral=True,
                )

            c = await interaction.channel.clone(
                reason=f"channel nuke requested by {ctx.author}"
            )

            if guild.system_channel and guild.system_channel.id == channel.id:
                await guild.edit(
                    system_channel=c, reason=f"channel nuke requested by {ctx.author}"
                )

            if (
                guild.public_updates_channel
                and guild.public_updates_channel.id == channel.id
            ):
                await guild.edit(
                    public_updates_channel=c,
                    reason=f"channel nuke requested by {ctx.author}",
                )

            if guild.rules_channel and guild.rules_channel.id == channel.id:
                await guild.edit(
                    rules_channel=c, reason=f"channel nuke requested by {ctx.author}"
                )

            await c.edit(position=ctx.channel.position)
            await ctx.channel.delete(reason=f"channel nuke requested by {ctx.author}")
            await c.send("first")

        async def no_callback(interaction: discord.Interaction):
            if not interaction.user:
                return await self.bot.ext.warning(
                    interaction,
                    "You are not the **author** of this embed",
                    ephemeral=True,
                )
            await interaction.response.edit_message(
                embed=discord.Embed(color=Colors.color, description="aborting action"),
                view=None,
            )

        yes.callback = yes_callback
        no.callback = no_callback
        view = discord.ui.View()
        view.add_item(yes)
        view.add_item(no)
        await ctx.reply(embed=embed, view=view)

    @commands.command(
        description="restore member's roles", brief="administrator", usage="[member]"
    )
    @Permissions.has_permission(administrator=True)
    async def restore(
        self,
        ctx: EvictContext,
        *,
        member: discord.Member,
        reason: str = "No Reason Provided",
    ):

        async with ctx.message.channel.typing():
            result = await self.bot.db.fetchrow(
                f"SELECT * FROM restore WHERE user_id = {member.id} AND guild_id = {ctx.guild.id}"
            )

            if result is None:
                return await ctx.warning(f"Unable to find saved roles for **{member}**")

            to_dump = json.loads(result["roles"])
            roles = [
                ctx.guild.get_role(r)
                for r in to_dump
                if ctx.guild.get_role(r) is not None
            ]

            succeed = ", ".join([f"{r.mention}" for r in roles if r.is_assignable()])
            failed = ", ".join([f"<@&{r.id}>" for r in roles if not r.is_assignable()])

            await member.edit(
                roles=[
                    r
                    for r in roles
                    if r.position
                    < ctx.guild.get_member(self.bot.user.id).top_role.position
                    and r != ctx.guild.premium_subscriber_role
                    and r != "@everyone"
                ],
                reason=reason + " | {}".format(ctx.author),
            )

            await ModConfig.sendlogs(
                self.bot,
                "restore",
                ctx.author,
                member,
                reason + " | " + str(ctx.author),
            )

            await self.bot.db.execute(
                f"DELETE FROM restore WHERE user_id = {member.id} AND guild_id = {ctx.guild.id}"
            )

            embed = discord.Embed(
                color=Colors.color,
                title="roles restored",
                description=f"target: **{member}**",
            )

            embed.set_thumbnail(url=member.display_avatar.url)

            embed.add_field(
                name="added",
                value="none" if succeed == ", " else succeed or "none",
                inline=False,
            )
            embed.add_field(
                name="failed",
                value="none" if failed == ", " else failed or "none",
                inline=False,
            )

            return await ctx.reply(embed=embed)

    @commands.command(
        aliases=["setnick", "nick"],
        description="change an user's nickname",
        usage="[member] <nickname>",
    )
    @Permissions.has_permission(manage_nicknames=True)
    async def nickname(
        self, ctx: EvictContext, target: discord.Member, *, nick: str = None
    ):

        if not Permissions.check_hierarchy(self.bot, ctx.author, target):
            return await ctx.warning(f"You cannot edit*{target.mention}")

        if nick == None:
            return await ctx.success(f"Cleared **{target.name}'s** nickname")

        await target.edit(nick=nick)
        return await ctx.success(f"Changed **{target.name}'s** nickname to **{nick}**")

    @commands.command(
        aliases=["uta"], description="untimeout all users", brief="moderate members"
    )
    @Permissions.has_permission(moderate_members=True)
    async def untimeoutall(self, ctx: EvictContext):
        for member in ctx.guild.members:
            if member.is_timed_out():
                await member.timeout(None, reason="Untimeout All")
                return await ctx.success("**unmuted** **all** members.")

    @Mod.is_mod_configured()
    @commands.command(
        description="kick members from your server",
        brief="kick members",
        usage="[member] <reason>",
    )
    @Permissions.has_permission(kick_members=True)
    async def kick(
        self,
        ctx: EvictContext,
        target: discord.Member,
        *,
        reason: str = "No Reason Provided",
    ):

        if not Permissions.check_hierarchy(self.bot, ctx.author, target):
            return await ctx.warning(f"You cannot kick*{target.mention}")

        await ctx.guild.kick(user=target, reason=reason + " | {}".format(ctx.author))

        await ModConfig.sendlogs(
            self.bot, "kick", ctx.author, target, reason + " | " + str(ctx.author)
        )

        if not await InvokeClass.invoke_send(ctx, target, reason):
            await ctx.success(f"**{target}** has been kicked | {reason}")

    @Mod.is_mod_configured()
    @commands.command(
        description="ban members from your server",
        brief="ban members",
        usage="[member] <reason>",
    )
    @Permissions.has_permission(ban_members=True)
    async def ban(
        self,
        ctx: EvictContext,
        target: Union[discord.Member, discord.User],
        *,
        reason: str = "No Reason Provided",
    ):

        if isinstance(target, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, target
        ):
            return await ctx.warning(f"You cannot ban*{target.mention}")

        await ctx.guild.ban(user=target, reason=reason + " | {}".format(ctx.author))

        await ModConfig.sendlogs(
            self.bot, "ban", ctx.author, target, reason + " | " + str(ctx.author)
        )

        if not await InvokeClass.invoke_send(ctx, target, reason):
            await ctx.success(f"**{target}** has been banned | {reason}")

    @commands.command(
        description="timeout members from your server",
        brief="moderate members",
        usage="[member] <reason>",
    )
    @Permissions.has_permission(moderate_members=True)
    async def mute(
        self,
        ctx: EvictContext,
        member: discord.Member,
        time: ValidTime = int,
        *,
        reason: str = "No reason provided",
    ):

        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot mute*{member.mention}")

        if member.is_timed_out():
            return await ctx.error(f"{member.mention} is **already** muted")

        if member.guild_permissions.administrator:
            return await ctx.warning("You **cannot** mute an administrator")

        await member.timeout(
            discord.utils.utcnow() + datetime.timedelta(seconds=time), reason=reason
        )

        if discord.Member:
            await ModConfig.sendlogs(
                self.bot, "mute", ctx.author, member, reason + " | " + str(ctx.author)
            )

        if not await InvokeClass.invoke_send(ctx, member, reason):
            await ctx.success(
                f"**{member}** has been muted for {humanfriendly.format_timespan(time)} | {reason}"
            )

    @commands.command(description="unban an user", usage="[member] [reason]")
    @Permissions.has_permission(ban_members=True)
    async def unban(
        self,
        ctx: EvictContext,
        member: discord.User,
        *,
        reason: str = "No reason provided",
    ):

        try:
            await ctx.guild.unban(
                user=member, reason=reason + f" | unbanned by {ctx.author}"
            )

            await ModConfig.sendlogs(
                self.bot, "unban", ctx.author, member, reason + " | " + str(ctx.author)
            )

            if not await InvokeClass.invoke_send(ctx, member, reason):
                await ctx.success(f"**{member}** has been unbanned")

        except discord.NotFound:
            return await ctx.warning(f"couldn't find ban for **{member}**")

    @commands.command(
        description="ban an user then immediately unban them",
        usage="[member] [reason]",
        brief="ban members",
    )
    @Permissions.has_permission(ban_members=True)
    async def softban(
        self,
        ctx: EvictContext,
        member: discord.Member,
        *,
        reason: str = "No reason provided",
    ):

        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot softban*{member.mention}")

        await member.ban(
            delete_message_days=7, reason=reason + f" | banned by {ctx.author}"
        )

        await ModConfig.sendlogs(
            self.bot, "softban", ctx.author, member, reason + " | " + str(ctx.author)
        )

        await ctx.guild.unban(user=member)
        await ctx.success(f"Softbanned **{member}**")

    @commands.command(
        description="unmute a member in your server",
        brief="moderate members",
        usage="[member] <reason>",
        aliases=["untimeout"],
    )
    @Permissions.has_permission(moderate_members=True)
    async def unmute(
        self,
        ctx: EvictContext,
        member: discord.Member,
        *,
        reason: str = "No reason provided",
    ):

        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot unmute*{member.mention}")

        if not member.is_timed_out():
            return await ctx.warning(f"**{member}** is not muted")

        await member.edit(
            timed_out_until=None, reason=reason + " | {}".format(ctx.author)
        )

        if not await InvokeClass.invoke_send(ctx, member, reason):
            await ctx.success(f"**{member}** has been unmuted")

        await ModConfig.sendlogs(self.bot, "unmute", ctx.author, member, reason)

    @commands.command(
        aliases=["vcmute"],
        description="mute a member in a voice channel",
        brief="moderate members",
        usage="[member]",
    )
    @Permissions.has_permission(moderate_members=True)
    async def voicemute(self, ctx: EvictContext, *, member: discord.Member):

        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot voicemute*{member.mention}")

        if not member.voice.channel:
            return await ctx.warning(f"**{member}** is **not** in a voice channel")

        if member.voice.self_mute:
            return await ctx.warning(f"**{member}** is **already** voice muted")

        await member.edit(mute=True, reason=f"Voice muted by {ctx.author}")
        await ModConfig.sendlogs(
            self.bot, "voicemute", ctx.author, member + " | " + str(ctx.author)
        )

        return await ctx.success(f"Voice muted **{member}**")

    @commands.command(
        aliases=["vcunmute"],
        description="unmute a member in a voice channel",
        brief="moderate members",
        usage="[member]",
    )
    @Permissions.has_permission(moderate_members=True)
    async def voiceunmute(self, ctx: EvictContext, *, member: discord.Member):

        if not member.voice.channel:
            return await ctx.warning(f"**{member}** is **not** in a voice channel")

        if not member.voice.self_mute:
            return await ctx.warning(f"**{member}** is **not** voice muted")

        await member.edit(mute=True, reason=f"Voice muted by {ctx.author}")
        await ModConfig.sendlogs(
            self.bot, "voiceunmute", ctx.author, member + " | " + str(ctx.author)
        )

        return await ctx.success(f"Voice muted **{member}**")

    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.group(name="clear", invoke_without_command=True)
    async def mata_clear(self, ctx: EvictContext):
        return await ctx.create_pages()

    @commands.cooldown(1, 3, commands.BucketType.guild)
    @mata_clear.command(
        description="clear messages that contain a certain word",
        usage="[word]",
        brief="manage messages",
    )
    async def contains(self, ctx: EvictContext, *, word: str):

        messages = [
            message
            async for message in ctx.channel.history(limit=300)
            if word in message.content
        ]

        if len(messages) == 0:

            return await ctx.warning(
                f"There are no messages containing **{word}** in this channel."
            )

        await ctx.channel.delete_messages(messages)

    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.command(
        aliases=["p"],
        description="bulk delete messages",
        brief="manage messages",
        usage="[messages]",
    )
    @Permissions.has_permission(manage_messages=True)
    async def purge(
        self, ctx: EvictContext, amount: int, *, member: discord.Member = None
    ):

        if member is None:
            await ctx.channel.purge(
                limit=amount + 1, bulk=True, reason=f"purge invoked by {ctx.author}"
            )

        messages = []

        async for m in ctx.channel.history():
            if m.author.id == member.id:
                messages.append(m)
            if len(messages) == amount:
                break

        messages.append(ctx.message)

        await ctx.channel.delete_messages(messages)

    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.command(
        description="bulk delete messages sent by bots",
        brief="manage messages",
        usage="[amount]",
        aliases=["bc", "botclear"],
    )
    @Permissions.has_permission(manage_messages=True)
    async def botpurge(self, ctx: EvictContext, amount: int = 100):

        mes = []

        async for message in ctx.channel.history():
            if len(mes) == amount:
                break
            if message.author.bot:
                mes.append(message)

        mes.append(ctx.message)
        await ctx.channel.delete_messages(mes)

    @Mod.is_mod_configured()
    @commands.command(
        description="removes all staff roles from a member",
        brief="administrator",
        usage="[member] [reason]",
    )
    @Permissions.has_permission(administrator=True)
    async def strip(
        self,
        ctx: EvictContext,
        member: discord.Member,
        *,
        reason: str = "No reason provided",
    ):
        if (
            ctx.author.top_role <= member.top_role
            and ctx.author.id not in self.bot.owner_ids
        ):
            return await ctx.warning(
                "You can't **strip** someone above you or someone with the same role as you."
            )

        await ctx.channel.typing()

        await member.edit(
            roles=[
                role
                for role in member.roles
                if not role.is_assignable()
                or not self.bot.ext.is_dangerous(role)
                or role.is_premium_subscriber()
            ],
            reason=reason + " | Moderator: {}".format(ctx.author),
        )

        await ctx.success(f"Removed **{member}'s** roles")
        await ModConfig.sendlogs(self.bot, "strip", ctx.author, member, reason)

    @commands.command(
        name="warn",
        description="warn a member",
        brief="manage messages",
        usage="[member] [reason]",
    )
    @Permissions.has_permission(manage_messages=True)
    async def warn(
        self,
        ctx: EvictContext,
        member: discord.Member,
        *,
        reason: str = "No reason provided",
    ):

        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot warn*{member.mention}")

        date = datetime.datetime.now()

        await self.bot.db.execute(
            "INSERT INTO warns VALUES ($1,$2,$3,$4,$5)",
            ctx.guild.id,
            member.id,
            ctx.author.id,
            f"{date.day}/{f'0{date.month}' if date.month < 10 else date.month}/{str(date.year)[-2:]} at {datetime.datetime.strptime(f'{date.hour}:{date.minute}', '%H:%M').strftime('%I:%M %p')}",
            reason,
        )

        if not await InvokeClass.invoke_send(ctx, member, reason):
            await ctx.success(f"warned **{member}** | {reason}")

        await ModConfig.sendlogs(self.bot, "warn", ctx.author, member, reason)

    @commands.command(
        name="warnclear",
        description="clear all warns from an user",
        usage="[member]",
        brief="manage messages",
    )
    @Permissions.has_permission(manage_messages=True)
    async def warnclear(self, ctx: EvictContext, *, member: discord.Member):

        check = await self.bot.db.fetch(
            "SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id,
        )

        if len(check) == 0:
            return await ctx.warning("This user has no warnings.")

        await self.bot.db.execute(
            "DELETE FROM warns WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id,
        )

        await ctx.success(f"Removed **{member.name}'s** warns")

    @commands.command(
        name="warnlist",
        aliases=["warns"],
        description="shows all warns of an user",
        usage="[member]",
    )
    @Permissions.has_permission(manage_messages=True)
    async def warnlist(self, ctx: EvictContext, *, member: discord.Member):

        check = await self.bot.db.fetch(
            "SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id,
        )

        warn_list = [
            f"``{index + 1}.`` {result['time']} - (``{result['reason']}``)"
            for index, result in enumerate(check)
        ]

        await ctx.paginate(warn_list, f"{member.name}'s warn list [{len(check)}]")

    @Mod.is_mod_configured()
    @commands.command(
        description="jail a member", usage="[member]", brief="manage channels"
    )
    @Permissions.has_permission(manage_channels=True)
    async def jail(
        self,
        ctx: EvictContext,
        member: discord.Member,
        *,
        reason: str = "No reason provided",
    ):

        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot jail*{member.mention}")

        check = await self.bot.db.fetchrow(
            "SELECT * FROM jail WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id,
        )

        if check:
            return await ctx.warning(f"**{member}** is already jailed")

        if reason == None:
            reason = "No reason provided"

        roles = [
            r.id for r in member.roles if r.name != "@everyone" and r.is_assignable()
        ]

        sql_as_text = json.dumps(roles)

        await self.bot.db.execute(
            "INSERT INTO jail VALUES ($1,$2,$3)", ctx.guild.id, member.id, sql_as_text
        )

        chec = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
        )

        roleid = chec["role_id"]

        try:
            jail = ctx.guild.get_role(roleid)
            new = [r for r in member.roles if not r.is_assignable()]
            new.append(jail)

            if not await InvokeClass.invoke_send(ctx, member, reason):
                await member.edit(
                    roles=new, reason=f"jailed by {ctx.author} - {reason}"
                )

            await ctx.success(f"**{member}** got jailed - {reason}")
            await ModConfig.sendlogs(self.bot, "jail", ctx.author, member, reason)

            c = ctx.guild.get_channel(int(chec["jail_id"]))

            if c:
                await c.send(
                    f"{member.mention}, you have been jailed! Wait for a staff member to unjail you and check direct messages if you have received one!"
                )
        except:
            return await ctx.error(f"There was a problem jailing **{member}**")

    @Mod.is_mod_configured()
    @commands.command(
        description="unjail a member",
        usage="[member] [reason]",
        brief="manage channels",
    )
    @Permissions.has_permission(manage_channels=True)
    async def unjail(
        self,
        ctx: EvictContext,
        member: discord.Member,
        *,
        reason: str = "No reason provided",
    ):

        check = await self.bot.db.fetchrow(
            "SELECT * FROM jail WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id,
        )

        if not check:
            return await ctx.warning(f"**{member}** is not jailed")

        chec = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
        )

        roleid = chec["role_id"]
        sq = check["roles"]
        roles = json.loads(sq)
        jail = ctx.guild.get_role(roleid)

        try:
            await member.edit(
                roles=[
                    ctx.guild.get_role(role)
                    for role in roles
                    if ctx.guild.get_role(role)
                ],
                reason=f"unjailed by {ctx.author}",
            )

        except:
            pass

        await self.bot.db.execute(
            "DELETE FROM jail WHERE user_id = {} AND guild_id = {}".format(
                member.id, ctx.guild.id
            )
        )

        if not await InvokeClass.invoke_send(ctx, member, reason):
            await ctx.success(f"Unjailed **{member}**")

        await ModConfig.sendlogs(self.bot, "unjail", ctx.author, member, reason)
        await member.remove_roles(jail)

    @commands.command(
        aliases=["sm"],
        description="add slowmode to a channel",
        usage="[seconds] <channel>",
        brief="manage channels",
    )
    @Permissions.has_permission(manage_channels=True)
    async def slowmode(
        self, ctx: EvictContext, seconds: str, channel: discord.TextChannel = None
    ):

        chan = channel or ctx.channel
        tim = humanfriendly.parse_timespan(seconds)

        await chan.edit(
            slowmode_delay=tim, reason="slowmode invoked by {}".format(ctx.author)
        )

        return await ctx.success(
            f"Slowmode for {channel.mention} set to **{humanfriendly.format_timespan(tim)}**"
        )

    @commands.group(invoke_without_command=True)
    @Permissions.has_permission(manage_channels=True)
    async def lock(self, ctx: EvictContext, channel: discord.TextChannel = None):

        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False

        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.success(f"I have **locked** {channel.mention}.")

        if channel is None:
            return await ctx.create_pages()

    @Permissions.has_permission(manage_channels=True)
    @lock.command(
        aliases=["viewlockall"],
        description="viewlock all channels",
        brief="manage channels",
    )
    async def viewall(self, ctx: EvictContext):
        for c in ctx.guild.channels:
            overwrite = c.overwrites_for(ctx.guild.default_role)
            overwrite.view_channel = False

            await c.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrite,
                reason=f"viewlocked by {ctx.author.name}",
            )

        await ctx.success("I have **viewlocked** all channels.")

    @Permissions.has_permission(manage_channels=True)
    @commands.command(description="lock all channels", brief="manage channels")
    async def lockall(self, ctx: EvictContext):

        for c in ctx.guild.channels:
            overwrite = c.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False

            await c.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrite,
                reason=f"locked by {ctx.author.name}",
            )

        await ctx.success("I have **locked** all channels.")

    @commands.group(invoke_without_command=True, name="unlock")
    @Permissions.has_permission(manage_channels=True)
    async def unlock(self, ctx: EvictContext, channel: discord.TextChannel = None):

        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True

        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.success(f"I have **unlocked** {channel.mention}.")

        if channel is None:
            return await ctx.create_pages()

    @Permissions.has_permission(manage_channels=True)
    @unlock.command(description="unlock all channels", brief="manage channels")
    async def all(self, ctx: EvictContext):

        for c in ctx.guild.channels:
            overwrite = c.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = True

            await c.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrite,
                reason=f"unlocked by {ctx.author.name}",
            )

        await ctx.success("I have **unlocked** all channels.")

    @Permissions.has_permission(manage_channels=True)
    @unlock.command(
        aliases=["unviewlockall"],
        description="unviewlock all channels",
        brief="manage channels",
    )
    async def viewall(self, ctx: EvictContext):

        for c in ctx.guild.channels:

            overwrite = c.overwrites_for(ctx.guild.default_role)
            overwrite.view_channel = True

            await c.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrite,
                reason=f"unviewlocked by {ctx.author.name}",
            )

        await ctx.success("I have **unviewlocked** all channels.")

    @Permissions.has_permission(manage_channels=True)
    @commands.command(
        name="imute",
        description="remove image permissions from a member",
        usage="[member] [channel]",
        brief="manage channels",
    )
    async def imute(
        self,
        ctx: EvictContext,
        member: discord.Member,
        channel: discord.TextChannel = None,
    ):

        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(member)
        overwrite.attach_files = False
        overwrite.embed_links = False

        await channel.set_permissions(member, overwrite=overwrite)
        await ctx.success(
            f"I have **removed** media permissions from **{member}** in {channel.mention}."
        )

    @Permissions.has_permission(manage_channels=True)
    @commands.command(
        name="iunmute",
        description="restore image permissions to a member",
        usage="[member] [channel]",
        brief="manage channels",
    )
    async def iunmute(
        self,
        ctx: EvictContext,
        member: discord.Member,
        channel: discord.TextChannel = None,
    ):

        channel = channel or ctx.channel

        overwrite = channel.overwrites_for(member)
        overwrite.attach_files = True
        overwrite.embed_links = True

        await channel.set_permissions(member, overwrite=overwrite)
        await ctx.success(
            f"I have **restored** media permissions to **{member}** in {channel.mention}."
        )

    @Permissions.has_permission(manage_channels=True)
    @commands.command(
        name="rmute",
        description="remove reaction permissions from a member",
        usage="[member] [channel]",
        brief="manage channels",
    )
    async def rmute(
        self,
        ctx: EvictContext,
        member: discord.Member,
        channel: discord.TextChannel = None,
    ):

        channel = channel or ctx.channel

        overwrite = channel.overwrites_for(member)
        overwrite.add_reactions = False

        await channel.set_permissions(member, overwrite=overwrite)
        await ctx.success(
            f"I have **removed** reaction permissions from **{member}** in {channel.mention}."
        )

    @Permissions.has_permission(manage_channels=True)
    @commands.command(
        name="runmute",
        description="restore reaction permissions to a member",
        usage="[member] [channel]",
        brief="manage channels",
    )
    async def runmute(
        self,
        ctx: EvictContext,
        member: discord.Member,
        channel: discord.TextChannel = None,
    ):

        channel = channel or ctx.channel

        overwrite = channel.overwrites_for(member)
        overwrite.add_reactions = True

        await channel.set_permissions(member, overwrite=overwrite)
        await ctx.success(
            f"I have **restored** reaction permissions to **{member}** in {channel.mention}."
        )

    @commands.group(
        invoke_without_command=True,
        description="manage roles in your server",
        aliases=["r"],
    )
    @Permissions.has_permission(manage_roles=True)
    async def role(
        self, ctx: EvictContext, user: discord.Member = None, *, role: GoodRole = None
    ):

        if role == None or user == None:
            return await ctx.create_pages()

        if role.is_premium_subscriber():
            return await ctx.warning("I **cannot** assign integrated roles to users.")

        if role in user.roles:
            await user.remove_roles(
                role, reason=f"{ctx.author} removed role from {user.name}"
            )
            return await ctx.success(f"Removed {role.mention} from **{user.name}**")

        else:
            await user.add_roles(role, reason=f"{ctx.author} added role to {user.name}")
            return await ctx.success(
                f"I have **added** {role.mention} to **{user.name}**."
            )

    @role.command(
        description="add a role to an user",
        usage="[user] [role]",
        name="add",
        brief="manage roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def role_add(
        self, ctx: EvictContext, user: discord.Member, *, role: GoodRole
    ):

        if role.is_premium_subscriber():
            return await ctx.warning("I **cannot** assign integrated roles to users.")

        if role in user.roles:
            return await ctx.error(f"**{user}** has this role already")

        await user.add_roles(role, reason=f"{ctx.author} added role to {user.name}")
        return await ctx.success(f"I have **added** {role.mention} to **{user.name}**.")

    @role.command(
        name="remove", brief="manage roles", description="remove a role from a member"
    )
    @Permissions.has_permission(manage_roles=True)
    async def role_remove(
        self, ctx: EvictContext, user: discord.Member, *, role: GoodRole
    ):

        if role.is_premium_subscriber():
            return await ctx.warning("I cant remove integrated roles from users.")

        if not role in user.roles:
            return await ctx.error(f"**{user}** doesn't have this role.")

        await user.remove_roles(
            role, reason=f"{ctx.author} removed role from {user.name}"
        )

        return await ctx.success(
            f"I have **removed** {role.mention} from **{user.name}**."
        )

    @role.command(description="create a role", usage="[name]", brief="manage roles")
    @Permissions.has_permission(manage_roles=True)
    async def create(self, ctx: EvictContext, *, name: str):
        role = await ctx.guild.create_role(name=name, reason=f"created by {ctx.author}")
        return await ctx.success(f"I have **created** the role {role.mention}")

    @role.command(description="delete a role", usage="[role]", brief="manage roles")
    @Permissions.has_permission(manage_roles=True)
    async def delete(self, ctx: EvictContext, *, role: GoodRole):
        await role.delete(reason=f"deleted by {ctx.author}")
        return await ctx.success(f"I have **deleted** the role {role.name}.")

    @role.group(
        invoke_without_command=True,
        name="humans",
        description="mass add or remove roles from members",
    )
    async def rolehumans(self, ctx: EvictContext):
        return await ctx.create_pages()

    @rolehumans.command(
        name="remove",
        description="remove a role from all members in this server",
        usage="[role]",
        brief="manage_roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def rolehumansremove(self, ctx: EvictContext, *, role: GoodRole):

        if self.bot.ext.is_dangerous(role):
            return await ctx.warning(
                "I **cannot** remove roles from users that have dangerous permissions."
            )

        if role.is_premium_subscriber():
            return await ctx.warning("I **cannot** remove integrated roles from users.")

        embed = discord.Embed(
            color=Colors.color,
            description=f"> {ctx.author.mention} I have started **removing** {role.mention} from all humans.",
        )

        message = await ctx.reply(embed=embed)

        try:
            for member in [m for m in ctx.guild.members if not m.bot]:
                if not role in member.roles:
                    continue
                await member.remove_roles(role, reason=f"{ctx.author}: massrole")

            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.approve} {ctx.author.mention}: I have **removed** {role.mention} from all humans.",
                )
            )

        except Exception:
            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.deny} {ctx.author.mention}: I was **unable** to remove {role.mention} from all humans.",
                )
            )

    @rolehumans.command(
        name="add",
        description="add a role to all humans in this server",
        usage="[role]",
        brief="manage_roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def rolehumansadd(self, ctx: EvictContext, *, role: GoodRole):

        if self.bot.ext.is_dangerous(role):
            return await ctx.warning(
                "I **cannot** assign roles to users that have dangerous permissions."
            )

        if role.is_premium_subscriber():
            return await ctx.warning("I **cannot** assign integrated roles to users.")

        embed = discord.Embed(
            color=Colors.color,
            description=f"> {ctx.author.mention}: I have started **adding** {role.mention} to all humans.",
        )

        message = await ctx.reply(embed=embed)

        try:
            for member in [m for m in ctx.guild.members if not m.bot]:
                if role in member.roles:
                    continue
                await member.add_roles(role, reason=f"{ctx.author}: massrole")

            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.approve} {ctx.author.mention}: I have **added** {role.mention} to all humans.",
                )
            )

        except Exception:
            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.deny} {ctx.author.mention}: I was **unable** to add {role.mention} to all humans.",
                )
            )

    @role.group(
        invoke_without_command=True,
        name="bots",
        description="mass add or remove roles from members",
    )
    async def rolebots(self, ctx: EvictContext):
        return await ctx.create_pages()

    @rolebots.command(
        name="remove",
        description="remove a role from all bots in this server",
        usage="[role]",
        brief="manage_roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def rolebotsremove(self, ctx: EvictContext, *, role: GoodRole):

        if self.bot.ext.is_dangerous(role):
            return await ctx.warning(
                "I **cannot** remove roles from bots that have dangerous permissions."
            )

        if role.is_premium_subscriber():
            return await ctx.warning("I **cannot** remove integrated roles from bots.")

        embed = discord.Embed(
            color=Colors.color,
            description=f"> {ctx.author.mention}: I have started **removing** {role.mention} from all bots.",
        )

        message = await ctx.reply(embed=embed)

        try:
            for member in [m for m in ctx.guild.members if m.bot]:

                if not role in member.roles:
                    continue

                await member.remove_roles(role, reason=f"{ctx.author}: massrole")

            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.approve} {ctx.author.mention}: I have **removed** {role.mention} from all bots.",
                )
            )

        except Exception:
            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.deny} {ctx.author.mention}: I was **unable** to remove {role.mention} from all bots.",
                )
            )

    @rolebots.command(
        name="add",
        description="add a role to all bots in this server",
        usage="[role]",
        brief="manage_roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def rolebotsadd(self, ctx: EvictContext, *, role: GoodRole):

        if self.bot.ext.is_dangerous(role):
            return await ctx.warning(
                "I **cannot** remove roles from users that have dangerous permissions."
            )

        if role.is_premium_subscriber():
            return await ctx.warning("I **cannot** assign integrated roles to bots.")

        embed = discord.Embed(
            color=Colors.color,
            description=f"> {ctx.author.mention}: **I have started **adding** {role.mention} to all bots.",
        )

        message = await ctx.reply(embed=embed)

        try:
            for member in [m for m in ctx.guild.members if m.bot]:
                if role in member.roles:
                    continue
                await member.add_roles(role, reason=f"{ctx.author}: massrole")

            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.approve} {ctx.author.mention}: I have **added** {role.mention} to all bots.",
                )
            )

        except Exception:
            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.deny} {ctx.author.mention}: I was **unable** to add {role.mention} to all bots.",
                )
            )

    @role.group(
        invoke_without_command=True,
        name="all",
        description="mass add or remove roles from members",
    )
    async def roleall(self, ctx: EvictContext):
        return await ctx.create_pages()

    @roleall.command(
        name="remove",
        description="remove a role from all members in this server",
        usage="[role]",
        brief="manage_roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def roleallremove(self, ctx: EvictContext, *, role: GoodRole):

        if role.is_premium_subscriber():
            return await ctx.warning("I **cannot** remove integrated roles from users.")

        embed = discord.Embed(
            color=Colors.color,
            description=f"> {ctx.author.mention} I have started **removing** {role.mention} from all members.",
        )

        message = await ctx.reply(embed=embed)

        try:
            for member in ctx.guild.members:
                if not role in member.roles:
                    continue
                await member.remove_roles(role, reason=f"{ctx.author}: massrole")

            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.approve} {ctx.author.mention}: I have **removed** {role.mention} from all members.",
                )
            )

        except Exception:
            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"> {Emojis.deny} {ctx.author.mention}: I was **unable** to remove {role.mention} from all members.",
                )
            )

    @roleall.command(
        name="add",
        description="add a role to all members in this server",
        usage="[role]",
        brief="manage_roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def rolealladd(self, ctx: EvictContext, *, role: GoodRole):

        if self.bot.ext.is_dangerous(role):
            return await ctx.warning(
                "I cant assign roles to users that have dangerous permissions."
            )

        if role.is_premium_subscriber():
            return await ctx.warning("I cant assign integrated roles to users.")

        embed = discord.Embed(
            color=Colors.color,
            description=f"{ctx.author.mention}: Adding {role.mention} to all members.",
        )
        message = await ctx.reply(embed=embed)

        try:
            for member in ctx.guild.members:
                if role in member.roles:
                    continue
                await member.add_roles(role, reason=f"{ctx.author}: massrole")

            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"{Emojis.approve} {ctx.author.mention}: Added {role.mention} to all members",
                )
            )

        except Exception:
            await message.edit(
                embed=discord.Embed(
                    color=Colors.color,
                    description=f"{Emojis.deny} {ctx.author.mention}: Unable to add {role.mention} to all members",
                )
            )

    @commands.group(name="autokick", aliases=["aks"], invoke_without_command=True)
    async def autokick(self, ctx: EvictContext):
        return await ctx.create_pages()

    @Mod.is_mod_configured()
    @autokick.command(
        name="add",
        description="add a user to be automatically kicked",
        brief="manage guild",
        usage="[user]",
    )
    @Permissions.has_permission(manage_guild=True)
    async def autokick_add(
        self, ctx: EvictContext, *, member: Union[discord.Member, discord.User]
    ):

        if isinstance(member, discord.Member) and not Permissions.check_hierarchy(
            self.bot, ctx.author, member
        ):
            return await ctx.warning(f"You cannot autokick*{member.mention}.")

        che = await self.bot.db.fetchrow(
            "SELECT * FROM autokick WHERE guild_id = {} AND autokick_users = {}".format(
                ctx.guild.id, member.id
            )
        )

        if che is not None:
            return await ctx.warning(
                f"**{member}** is **already** on the autokick list."
            )

        await ctx.guild.kick(member, reason="autokicked by {}".format(ctx.author))

        await self.bot.db.execute(
            "INSERT INTO autokick VALUES ($1,$2,$3)",
            ctx.guild.id,
            member.id,
            ctx.author.id,
        )

        await ctx.success(f"I have **added** **{member}** to autokick list.")

    @Mod.is_mod_configured()
    @autokick.command(
        name="remove",
        description="remove a user from being automatically kicked",
        brief="manage guild",
        usage="[user]",
    )
    @Permissions.has_permission(manage_guild=True)
    async def autokick_remove(self, ctx: EvictContext, *, member: discord.User):

        che = await self.bot.db.fetchrow(
            "SELECT * FROM autokick WHERE guild_id = {} AND autokick_users = {}".format(
                ctx.guild.id, member.id
            )
        )

        if che is None:
            return await ctx.warning(f"**{member}** is not on autokick list.")

        await self.bot.db.execute(
            "DELETE FROM autokick WHERE autokick_users = {}".format(member.id)
        )

        await ctx.success(f"I have **removed** **{member}** from autokick list.")

    @Mod.is_mod_configured()
    @Permissions.has_permission(manage_guild=True)
    @autokick.command(
        name="list", description="check autokick list", brief="manage guild"
    )
    async def autokick_list(self, ctx: EvictContext):
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        results = await self.bot.db.fetch(
            "SELECT * FROM autokick WHERE guild_id = $1", ctx.guild.id
        )
        if len(results) == 0:
            return await ctx.warning("no **autokick** members found")
        for result in results:
            mes = f"{mes}`{k}` {await self.bot.fetch_user(result['autokick_users'])}\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=Colors.color,
                        title=f"autokick list [{len(results)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(
            discord.Embed(
                color=Colors.color,
                title=f"autokick list [{len(results)}]",
                description=messages[i],
            )
        )
        await ctx.paginate(number)

    @commands.group(name="private", invoke_without_command=True)
    async def private(self, ctx):
        return await ctx.create_pages()

    @Mod.is_mod_configured()
    @private.command(
        name="unwhitelist",
        description="unwhitelist a user from not being affected by private",
        brief="manage guild",
        usage="[user]",
    )
    @Permissions.has_permission(manage_guild=True)
    async def private_unwhitelist(self, ctx: EvictContext, *, member: discord.User):

        che = await self.bot.db.fetchrow(
            "SELECT * FROM private WHERE guild_id = {} AND private_users = {}".format(
                ctx.guild.id, member.id
            )
        )

        if che is None:
            return await ctx.warning(f"**{member}** is **not** on private whitelist.")

        await self.bot.db.execute(
            "DELETE FROM private WHERE guild_id = {} AND private_users = {}".format(
                ctx.guild.id, member.id
            )
        )

        await ctx.success(f"I have **removed** **{member}** from private whitelist.")

    @Mod.is_mod_configured()
    @private.command(
        name="whitelist",
        description="whitelist a user from being affected by private",
        brief="manage guild",
        usage="[user]",
    )
    @Permissions.has_permission(manage_guild=True)
    async def private_whitelist(
        self, ctx: EvictContext, *, member: Union[discord.Member, discord.User]
    ):

        che = await self.bot.db.fetchrow(
            "SELECT * FROM private WHERE guild_id = {} AND user_id = {}".format(
                ctx.guild.id, member.id
            )
        )
        if che is not None:
            return await ctx.warning(
                f"**{member}** is **already** on the private whitelist."
            )

        await self.bot.db.execute(
            "INSERT INTO private VALUES ($1,$2)", ctx.guild.id, member.id
        )

        return await ctx.success(f"I have **added** **{member}** to private whitelist.")

    @private.command(
        name="enable", description="enable the private module", brief="manage guild"
    )
    @Permissions.has_permission(manage_guild=True)
    async def private_enable(self, ctx: EvictContext):

        private = await self.bot.db.fetchrow(
            "SELECT * FROM private WHERE guild_id = $1", ctx.guild.id
        )

        if private is not None:
            return await ctx.warning("The server has **already** been set to private.")

        await self.bot.db.execute("INSERT INTO private VALUES ($1)", ctx.guild.id)

        return await ctx.success(
            "I have marked the server as private, new members will be automatically **kicked**."
        )

    @private.command(
        name="disable", description="disable the private module", brief="manage guild"
    )
    @Permissions.has_permission(manage_guild=True)
    async def private_disable(self, ctx: EvictContext):

        private = await self.bot.db.fetchrow(
            "SELECT * FROM private WHERE guild_id = $1", ctx.guild.id
        )

        if private is None:
            return await ctx.warning(f"The server is not set to private.")

        await self.bot.db.execute(
            "DELETE FROM private WHERE guild_id = $1", ctx.guild.id
        )

        return await ctx.success(
            "I have unmarked the server as private, new members will **not** be kicked."
        )

    @Permissions.has_permission(administrator=True)
    @private.command(
        name="list",
        description="check private whitelist",
        brief="donor & administrator",
    )
    async def private_list(self, ctx: EvictContext):

        results = await self.bot.db.fetch(
            "SELECT * FROM private WHERE guild_id = $1", ctx.guild.id
        )

        private_list = [
            f"``{index + 1}.`` {await self.bot.fetch_user(result['user_id'])} (``{result['user_id']}``)"
            for index, result in enumerate(results)
        ]

        await ctx.paginate(private_list, f"uwulocked list [{len(results)}]")


async def setup(bot: Evict):
    await bot.add_cog(moderation(bot))
