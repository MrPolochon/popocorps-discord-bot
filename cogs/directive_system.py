import discord
from discord.ext import commands
from discord import app_commands
import logging

from models import Directive, get_db_session, create_tables


class DirectiveSystem(commands.Cog):
    """Système de directives : un admin définit des règles permettant à une
    personne (ou un rôle) autorisée de faire exécuter une action au bot
    (donner / retirer un rôle) en mentionnant un membre avec un mot-déclencheur.
    La personne autorisée n'a PAS besoin d'être admin pour déclencher l'action.
    """

    directive_group = app_commands.Group(
        name="directive",
        description="Gérer les directives du bot (admin)",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    def __init__(self, bot):
        self.bot = bot
        try:
            create_tables()
        except Exception as e:
            logging.error(f"Directive: impossible de creer les tables: {e}")

    # ---------- Helpers base de données ----------

    def _get_guild_directives(self, guild_id):
        """Retourne les directives d'un serveur sous forme de dictionnaires simples."""
        db = get_db_session()
        try:
            rows = db.query(Directive).filter(Directive.guild_id == guild_id).all()
            return [
                {
                    "id": d.id,
                    "trigger": d.trigger,
                    "action": d.action,
                    "role_id": d.role_id,
                    "authorized_type": d.authorized_type,
                    "authorized_id": d.authorized_id,
                }
                for d in rows
            ]
        except Exception as e:
            logging.error(f"Directive: erreur de lecture: {e}")
            return []
        finally:
            db.close()

    # ---------- Commandes ----------

    @directive_group.command(name="add", description="Créer une directive")
    @app_commands.describe(
        trigger="Mot-déclencheur (ex: whitelist)",
        action="Action à exécuter",
        role="Rôle à donner ou retirer",
        authorized_user="Personne autorisée à déclencher (laisser vide si tu utilises un rôle)",
        authorized_role="Rôle autorisé à déclencher (laisser vide si tu utilises une personne)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Donner le rôle", value="give_role"),
            app_commands.Choice(name="Retirer le rôle", value="remove_role"),
        ]
    )
    async def add_directive(
        self,
        interaction: discord.Interaction,
        trigger: str,
        action: app_commands.Choice[str],
        role: discord.Role,
        authorized_user: discord.Member = None,
        authorized_role: discord.Role = None,
    ):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Il te faut la permission *Gérer le serveur* pour créer une directive.",
                ephemeral=True,
            )
            return

        # Exactement une cible autorisée
        if (authorized_user is None) == (authorized_role is None):
            await interaction.response.send_message(
                "❌ Choisis **soit** une personne autorisée **soit** un rôle autorisé (pas les deux, pas aucun).",
                ephemeral=True,
            )
            return

        trigger_clean = trigger.strip().lower()
        if not trigger_clean:
            await interaction.response.send_message("❌ Le mot-déclencheur ne peut pas être vide.", ephemeral=True)
            return

        # Vérifie la hiérarchie pour que le bot puisse gérer ce rôle
        me = interaction.guild.me
        if not me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "⚠️ Attention : il me manque la permission *Gérer les rôles*. La directive sera créée mais ne pourra pas s'exécuter tant que je ne l'ai pas.",
                ephemeral=True,
            )
        elif role >= me.top_role:
            await interaction.response.send_message(
                f"⚠️ Attention : le rôle **{role.name}** est au-dessus de mon rôle le plus haut. Je ne pourrai pas l'attribuer tant que mon rôle n'est pas plus haut.",
                ephemeral=True,
            )

        if authorized_user is not None:
            auth_type, auth_id, auth_label = "user", authorized_user.id, authorized_user.mention
        else:
            auth_type, auth_id, auth_label = "role", authorized_role.id, authorized_role.mention

        db = get_db_session()
        try:
            directive = Directive(
                guild_id=interaction.guild.id,
                trigger=trigger_clean,
                action=action.value,
                role_id=role.id,
                authorized_type=auth_type,
                authorized_id=auth_id,
                created_by=interaction.user.id,
            )
            db.add(directive)
            db.commit()
            directive_id = directive.id
        except Exception as e:
            db.rollback()
            logging.error(f"Directive: erreur de creation: {e}")
            await interaction.response.send_message("❌ Erreur lors de l'enregistrement de la directive.", ephemeral=True)
            return
        finally:
            db.close()

        action_label = "donner" if action.value == "give_role" else "retirer"
        embed = discord.Embed(
            title="✅ Directive créée",
            description=(
                f"**#{directive_id}** — Quand {auth_label} écrit « **{trigger_clean}** » en mentionnant un membre, "
                f"je vais **{action_label}** le rôle {role.mention}."
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text="La personne/le rôle autorisé n'a pas besoin d'être admin pour déclencher l'action.")
        await interaction.response.send_message(embed=embed)

    @directive_group.command(name="list", description="Voir les directives configurées")
    async def list_directives(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Il te faut la permission *Gérer le serveur*.", ephemeral=True
            )
            return

        directives = self._get_guild_directives(interaction.guild.id)
        if not directives:
            await interaction.response.send_message(
                "📭 Aucune directive configurée. Crée-en une avec `/directive add`.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📋 Directives du serveur",
            color=discord.Color.blurple(),
        )
        for d in directives:
            if d["authorized_type"] == "user":
                auth = f"<@{d['authorized_id']}>"
            else:
                auth = f"<@&{d['authorized_id']}>"
            action_label = "donner" if d["action"] == "give_role" else "retirer"
            embed.add_field(
                name=f"#{d['id']} — « {d['trigger']} »",
                value=f"Autorisé : {auth}\nAction : **{action_label}** le rôle <@&{d['role_id']}>",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @directive_group.command(name="remove", description="Supprimer une directive")
    @app_commands.describe(directive_id="Numéro de la directive (visible dans /directive list)")
    async def remove_directive(self, interaction: discord.Interaction, directive_id: int):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ Il te faut la permission *Gérer le serveur*.", ephemeral=True
            )
            return

        db = get_db_session()
        try:
            directive = (
                db.query(Directive)
                .filter(Directive.id == directive_id, Directive.guild_id == interaction.guild.id)
                .first()
            )
            if not directive:
                await interaction.response.send_message(
                    f"❌ Aucune directive #{directive_id} sur ce serveur.", ephemeral=True
                )
                return
            db.delete(directive)
            db.commit()
        except Exception as e:
            db.rollback()
            logging.error(f"Directive: erreur de suppression: {e}")
            await interaction.response.send_message("❌ Erreur lors de la suppression.", ephemeral=True)
            return
        finally:
            db.close()

        await interaction.response.send_message(f"🗑️ Directive #{directive_id} supprimée.")

    # ---------- Déclenchement ----------

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        directives = self._get_guild_directives(message.guild.id)
        if not directives:
            return

        content_lower = message.content.lower()
        author_role_ids = {r.id for r in getattr(message.author, "roles", [])}
        # Cibles = membres mentionnés qui ne sont ni le bot ni l'auteur
        targets = [m for m in message.mentions if not m.bot and m.id != message.author.id]

        for d in directives:
            # 1) L'auteur est-il autorisé pour cette directive ?
            if d["authorized_type"] == "user":
                if message.author.id != d["authorized_id"]:
                    continue
            else:  # role
                if d["authorized_id"] not in author_role_ids:
                    continue

            # 2) Le mot-déclencheur est-il présent ?
            if d["trigger"] not in content_lower:
                continue

            # 3) Y a-t-il un membre ciblé ?
            if not targets:
                await message.channel.send(
                    "🤔 J'ai bien reconnu la directive, mais mentionne la personne concernée (ex: `"
                    f"{d['trigger']} @membre`)."
                )
                return

            await self._execute_directive(message, d, targets[0])
            return

    async def _execute_directive(self, message, directive, target):
        guild = message.guild
        role = guild.get_role(directive["role_id"])
        if role is None:
            await message.channel.send("⚠️ Le rôle configuré dans cette directive n'existe plus.")
            return

        me = guild.me
        if not me.guild_permissions.manage_roles:
            await message.channel.send("⚠️ Il me manque la permission *Gérer les rôles* pour faire ça.")
            return
        if role >= me.top_role:
            await message.channel.send(
                f"⚠️ Je ne peux pas gérer le rôle **{role.name}** : il est au-dessus de mon rôle dans la hiérarchie. "
                "Monte mon rôle au-dessus dans les paramètres du serveur."
            )
            return

        reason = f"Directive '{directive['trigger']}' déclenchée par {message.author} ({message.author.id})"
        try:
            if directive["action"] == "give_role":
                if role in target.roles:
                    await message.channel.send(f"ℹ️ {target.mention} a déjà le rôle **{role.name}**.")
                    return
                await target.add_roles(role, reason=reason)
                await message.channel.send(
                    f"✅ C'est fait ! J'ai donné le rôle **{role.name}** à {target.mention} 🛡️"
                )
            else:  # remove_role
                if role not in target.roles:
                    await message.channel.send(f"ℹ️ {target.mention} n'a pas le rôle **{role.name}**.")
                    return
                await target.remove_roles(role, reason=reason)
                await message.channel.send(
                    f"✅ J'ai retiré le rôle **{role.name}** à {target.mention}."
                )
        except discord.Forbidden:
            await message.channel.send("⚠️ Discord a refusé l'action (permissions/hiérarchie).")
        except Exception as e:
            logging.error(f"Directive: erreur d'execution: {e}")
            await message.channel.send("❌ Une erreur est survenue lors de l'exécution de la directive.")


async def setup(bot):
    await bot.add_cog(DirectiveSystem(bot))
