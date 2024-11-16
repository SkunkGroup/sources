from AAA3A_utils import Cog, CogsUtils, Menu  # isort:skip
from grief.core import commands  # isort:skip
from grief.core.i18n import Translator, cog_i18n  # isort:skip
from grief.core.bot import Grief  # isort:skip
import discord  # isort:skip
import typing  # isort:skip
import logging
from discord.ext import tasks

import datetime
import re

from grief.core.commands.converter import get_timedelta_converter
from grief.core.utils.chat_formatting import box, pagify
from grief.core import Config

try:
    from emoji import UNICODE_EMOJI_ENGLISH as EMOJI_DATA  # emoji<2.0.0
except ImportError:
    from emoji import EMOJI_DATA  # emoji>=2.0.0

log = logging.getLogger("grief.admin")

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)

def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated
ERROR_MESSAGE = _("I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}")

_ = Translator("DiscordEdit", __file__)


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Union[discord.PartialEmoji, str]:
        argument = argument.strip("\N{VARIATION SELECTOR-16}")
        if argument in EMOJI_DATA:
            return argument
        return await super().convert(ctx, argument=argument)


class ForumTagConverter(discord.ext.commands.Converter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> typing.Tuple[discord.Role, typing.Union[discord.PartialEmoji, str]]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            try:
                name, emoji, moderated = arg_split
            except Exception:
                name, emoji = arg_split
                moderated = False
        except Exception:
            raise commands.BadArgument(
                _(
                    "Emoji Role must be an emoji followed by a role separated by either `;`, `,`, `|`, or `-`."
                )
            )
        emoji = await Emoji().convert(ctx, emoji.strip())
        return discord.ForumTag(name=name, emoji=emoji, moderated=moderated)


@cog_i18n(_)
class EditThread(Cog):
    """A cog to edit threads!"""

    def __init__(self, bot: Grief) -> None:  # Never executed except manually.
        super().__init__(bot=bot)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        self.config.register_guild(threads=[])
        self.bump_threads.start()

    async def check_thread(self, ctx: commands.Context, thread: typing.Optional[discord.Thread]) -> bool:
        # if (
        #     not thread.permissions_for(ctx.author).manage_channels
        #     and ctx.author.id != ctx.guild.owner.id
        #     and ctx.author.id not in ctx.bot.owner_ids
        #     and ctx.author != thread.owner
        # ):
        #     raise commands.UserFeedbackCheckFailure(
        #         _(
        #             "I can not let you edit the thread {thread.mention} ({thread.id}) because I don't have the `manage_channel` permission."
        #         ).format(thread=thread)
        #     )
        if not thread.permissions_for(ctx.me).manage_channels:
            raise commands.UserFeedbackCheckFailure(
                _(
                    "I can not edit the thread {thread.mention} ({thread.id}) because you don't have the `manage_channel` permission."
                ).format(thread=thread)
            )
        return True

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.hybrid_group()
    async def editthread(self, ctx: commands.Context) -> None:
        """Commands for edit a text channel."""
        pass

    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="create")
    async def editthread_create(
        self,
        ctx: commands.Context,
        channel: typing.Optional[discord.TextChannel] = None,
        message: typing.Optional[commands.MessageConverter] = None,
        *,
        name: str,
    ) -> None:
        """Create a thread.
        
        You'll join it automatically.
        """
        if channel is None:
            channel = ctx.channel
        try:
            thread = await channel.create_thread(
                name=name,
                message=message,
                reason=f"{ctx.author} ({ctx.author.id}) has created the thread #{name}.",
            )
            await thread.add_user(ctx.author)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @editthread.command(name="list")
    async def editthread_list(
        self,
        ctx: commands.Context,
    ) -> None:
        """List all threads in the current guild."""
        description = "\n".join(
            [
                f"**•** {thread.mention} ({thread.id}) - {len(await thread.fetch_members())} members"
                for thread in ctx.guild.threads
            ]
        )
        embed: discord.Embed = discord.Embed(color=await ctx.embed_color())
        embed.title = _("List of threads in {guild.name} ({guild.id})").format(guild=ctx.guild)
        embeds = []
        pages = pagify(description, page_length=4096)
        for page in pages:
            e = embed.copy()
            e.description = page
            embeds.append(e)
        await Menu(pages=embeds).start(ctx)

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="name")
    async def editthread_name(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], name: str
    ) -> None:
        """Edit thread name."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="archived")
    async def editthread_archived(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], archived: bool = None
    ) -> None:
        """Edit thread archived."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        archived = not thread.archived
        try:
            await thread.edit(
                archived=archived,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="locked")
    async def editthread_locked(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], locked: bool = None
    ) -> None:
        """Edit thread locked."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        if locked is None:
            locked = not thread.locked
        try:
            await thread.edit(
                locked=locked,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="pinned")
    async def editthread_pinned(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], pinned: bool
    ) -> None:
        """Edit thread pinned."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                pinned=pinned,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="invitable")
    async def editthread_invitable(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], invitable: bool = None
    ) -> None:
        """Edit thread invitable."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        if invitable is None:
            invitable = not thread.invitable
        try:
            await thread.edit(
                invitable=invitable,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="autoarchiveduration")
    async def editthread_auto_archive_duration(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        auto_archive_duration: typing.Literal["60", "1440", "4320", "10080"],
    ) -> None:
        """Edit thread auto archive duration."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                auto_archive_duration=auto_archive_duration,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="slowmodedelay")
    async def editthread_slowmode_delay(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], slowmode_delay: TimedeltaConverter
    ) -> None:
        """Edit thread slowmode delay."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                slowmode_delay=slowmode_delay,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="appliedtags")
    async def editthread_applied_tags(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        applied_tags: commands.Greedy[ForumTagConverter],
    ) -> None:
        """Edit thread applied tags.

        ```
        [p]editthread appliedtags "<name>|<emoji>|[moderated]"
        [p]editthread appliedtags "Reporting|⚠️|True" "Bug|🐛"
        ```
        """
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        try:
            await thread.edit(
                applied_tags=list(applied_tags),
                reason=f"{ctx.author} ({ctx.author.id}) has edited the thread #{thread.name} ({thread.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="adduser", aliases=["addmember"])
    async def editthread_add_user(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], member: discord.Member
    ) -> None:
        """Add member to thread."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        if discord.utils.get(await thread.fetch_members(), id=member.id) is not None:
            raise commands.UserFeedbackCheckFailure("This member is already in this thread.")
        await self.check_thread(ctx, thread)
        try:
            await thread.add_user(member)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="removeuser", aliases=["removemember"])
    async def editthread_remove_user(
        self, ctx: commands.Context, thread: typing.Optional[discord.Thread], member: discord.Member
    ) -> None:
        """Remove member from thread."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        try:
            await thread.remove_user(member)
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @editthread.command(name="delete")
    async def editthread_delete(
        self,
        ctx: commands.Context,
        thread: typing.Optional[discord.Thread],
        confirmation: bool = False,
    ) -> None:
        """Delete a thread."""
        if thread is None:
            if isinstance(ctx.channel, discord.Thread):
                thread = ctx.channel
            else:
                await ctx.send_help()
                return
        await self.check_thread(ctx, thread)
        if not confirmation and not ctx.assume_yes:
            if ctx.bot_permissions.embed_links:
                embed: discord.Embed = discord.Embed()
                embed.title = _("⚠️ - Delete thread")
                embed.description = _(
                    "Do you really want to delete the thread {thread.mention} ({thread.id})?"
                ).format(thread=thread)
                embed.color = 0xF00020
                content = ctx.author.mention
            else:
                embed = None
                content = f"{ctx.author.mention} " + _(
                    "Do you really want to delete the thread {thread.mention} ({thread.id})?"
                ).format(thread=thread)
            if not await CogsUtils.ConfirmationAsk(
                ctx, content=content, embed=embed
            ):
                await CogsUtils.delete_message(ctx.message)
                return
        try:
            await thread.delete()  # Not supported: reason=f"{ctx.author} ({ctx.author.id}) has deleted the thread #{thread.name} ({thread.id})."
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
        
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def keepalive(self, ctx, thread: discord.Thread):
        """
        Sends a ping to the thread to keep it alive.
        """
        async with self.config.guild(ctx.guild).threads() as threads:
            if thread.id in threads:
                threads.remove(thread.id)
                await ctx.send(
                    f"{thread.mention} under {thread.parent.mention} is no longer being bumped."
                )
            else:
                threads.append(thread.id)
                await ctx.send(
                    f"{thread.mention} under {thread.parent.mention} is now being bumped."
                )

    @tasks.loop(hours=12)
    async def bump_threads(self):
        config = await self.config.all_guilds()
        for guild_id, guild_data in config.items():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue

            for thread_id in guild_data["threads"]:
                thread = guild.get_thread(thread_id)
                if thread is None:
                    continue
                await thread.edit(archived=False, auto_archive_duration=60)
                await thread.edit(archived=False, auto_archive_duration=1440)
                log.debug(f"Thread {thread.id} was bumped")