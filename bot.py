import discord
from discord.ext import commands
import asyncio
import os # Importe le module 'os' pour accéder aux variables d'environnement

# --- Configuration ---
# REMPLACEZ CES VALEURS PAR LES VÔTRES SI ELLES CHANGENT !
# --------------------------------------------------------------------------------------------------------------------
# Le token est maintenant lu depuis une variable d'environnement pour la sécurité et l'hébergement.
# Sur Render, vous devrez créer une variable d'environnement nommée 'DISCORD_TOKEN'
# et y coller le token de votre bot.
TOKEN = os.getenv('DISCORD_TOKEN')

# Vérification pour s'assurer que le token est bien défini
if TOKEN is None:
    print("ERREUR: La variable d'environnement 'DISCORD_TOKEN' n'est pas définie.")
    print("Veuillez la définir sur votre plateforme d'hébergement (ex: Render) avant de lancer le bot.")
    # Pour un environnement de développement local, vous pouvez décommenter la ligne ci-dessous
    # et y mettre votre token pour tester, mais NE LA LAISSEZ PAS POUR LE DÉPLOIEMENT !
    # TOKEN = 'VOTRE_TOKEN_DU_BOT_POUR_TEST_LOCAL'
    exit() # Arrête le script si le token n'est pas trouvé

# IDs tirés de votre image
GUILD_ID = 1412500289784778835
ONBOARDING_CHANNEL_ID = 1424356640198758451

# IDs des rôles
ROLE_JOUEUR_PC_ID = 1414309241594056705
ROLE_YOUTUBEUR_ID = 1414310188072042516
ROLE_HACKER_ID = 1414310468964581489
ROLE_JOUEUR_PS3_ID = 1414310001077518367
ROLE_MEMBRE_ID = 1414309080612343828
# --------------------------------------------------------------------------------------------------------------------


# --- Intents ---
# Il est crucial d'activer les intents nécessaires pour que le bot fonctionne correctement.
# Assurez-vous que 'SERVER MEMBERS INTENT' est activé dans le portail développeur Discord.
intents = discord.Intents.default()
intents.members = True          # Nécessaire pour l'événement on_member_join
intents.message_content = True  # Nécessaire si vous utilisez des commandes textuelles (ex: !ping)
intents.guilds = True           # Nécessaire pour les événements de guilde

bot = commands.Bot(command_prefix='!', intents=intents)

# --- Gestion de l'état du questionnaire ---
# Dictionnaire pour suivre où chaque utilisateur en est dans le questionnaire.
# Format: {user_id: current_question_index}
user_onboarding_state = {}

# Liste des questions et des rôles associés.
# Si l'utilisateur répond "Oui" à une question, le rôle correspondant lui est attribué.
QUESTIONS = [
    {"question": "As-tu un PC pour jouer ?", "role_id": ROLE_JOUEUR_PC_ID},
    {"question": "As-tu une PS3 ?", "role_id": ROLE_JOUEUR_PS3_ID},
    {"question": "As-tu une chaîne YouTube ?", "role_id": ROLE_YOUTUBEUR_ID},
    {"question": "As-tu déjà fait du hacking ?", "role_id": ROLE_HACKER_ID},
]

# --- Classe pour les boutons du questionnaire ---
class OnboardingView(discord.ui.View):
    def __init__(self, member: discord.Member, current_question_index: int):
        super().__init__(timeout=300) # Le questionnaire expirera après 5 minutes d'inactivité
        self.member = member
        self.current_question_index = current_question_index
        self.message = None # Pour stocker le message du questionnaire afin de le modifier

    # Cette fonction est appelée si l'utilisateur ne répond pas dans le temps imparti
    async def on_timeout(self):
        if self.message:
            await self.message.edit(content="Le questionnaire a expiré. Veuillez contacter un administrateur si vous souhaitez le refaire.", view=None)
        user_onboarding_state.pop(self.member.id, None) # Nettoyer l'état de l'utilisateur

    # Fonction pour envoyer la question suivante ou terminer le questionnaire
    async def send_next_question(self, interaction: discord.Interaction):
        self.current_question_index += 1
        user_onboarding_state[self.member.id] = self.current_question_index

        if self.current_question_index < len(QUESTIONS):
            # Il reste des questions, envoyer la suivante
            next_question_data = QUESTIONS[self.current_question_index]
            await interaction.response.edit_message(
                content=next_question_data["question"],
                view=OnboardingView(self.member, self.current_question_index)
            )
        else:
            # Toutes les questions ont été répondues
            await interaction.response.edit_message(content="Merci d'avoir répondu au questionnaire ! Vous avez maintenant accès au serveur.", view=None)
            
            # Attribuer le rôle "membre" final
            guild = self.member.guild
            member_role = guild.get_role(ROLE_MEMBRE_ID)
            if member_role:
                await self.member.add_roles(member_role, reason="Questionnaire d'intégration terminé")
                print(f"Rôle 'membre' attribué à {self.member.display_name}")
            else:
                print(f"Erreur: Rôle 'membre' (ID: {ROLE_MEMBRE_ID}) introuvable. Veuillez vérifier l'ID.")
            
            user_onboarding_state.pop(self.member.id, None) # Nettoyer l'état de l'utilisateur

    # Bouton "Oui"
    @discord.ui.button(label="Oui", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # S'assurer que seul l'utilisateur concerné peut interagir avec ses boutons
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Ce n'est pas votre questionnaire !", ephemeral=True)
            return

        current_question_data = QUESTIONS[self.current_question_index]
        role_to_add = self.member.guild.get_role(current_question_data["role_id"])
        if role_to_add:
            await self.member.add_roles(role_to_add, reason=f"Réponse 'Oui' au questionnaire: {current_question_data['question']}")
            print(f"Rôle '{role_to_add.name}' attribué à {self.member.display_name}")
        else:
            print(f"Erreur: Rôle (ID: {current_question_data['role_id']}) introuvable pour la question: {current_question_data['question']}. Veuillez vérifier l'ID.")
        
        await self.send_next_question(interaction)

    # Bouton "Non"
    @discord.ui.button(label="Non", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # S'assurer que seul l'utilisateur concerné peut interagir avec ses boutons
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("Ce n'est pas votre questionnaire !", ephemeral=True)
            return
        
        # Pas de rôle à ajouter pour "Non", on passe juste à la question suivante
        print(f"Réponse 'Non' de {self.member.display_name} à la question: {QUESTIONS[self.current_question_index]['question']}")
        await self.send_next_question(interaction)

# --- Événements du bot ---

# Quand le bot est prêt et connecté
@bot.event
async def on_ready():
    print(f'Bot connecté en tant que {bot.user.name} (ID: {bot.user.id})')
    print(f'Version de discord.py: {discord.__version__}')
    print('Prêt à l\'action !')

# Quand un nouveau membre rejoint le serveur
@bot.event
async def on_member_join(member: discord.Member):
    # S'assurer que l'événement provient du bon serveur
    if member.guild.id != GUILD_ID:
        return

    print(f'{member.display_name} a rejoint le serveur. Démarrage du questionnaire.')

    # Vérifier si l'utilisateur est déjà en train de faire le questionnaire (pour éviter les doublons)
    if member.id in user_onboarding_state:
        print(f"{member.display_name} est déjà en cours de questionnaire. Ignoré.")
        return

    # Initialiser l'état du questionnaire pour ce membre à la première question (index 0)
    user_onboarding_state[member.id] = 0

    # Récupérer le salon où envoyer le questionnaire
    channel = bot.get_channel(ONBOARDING_CHANNEL_ID)
    if channel:
        first_question_data = QUESTIONS[0]
        view = OnboardingView(member, 0)
        # Envoyer le message de bienvenue avec la première question et les boutons
        message = await channel.send(
            f"Bienvenue {member.mention} sur le serveur ! Pour commencer, veuillez répondre à quelques questions :\n\n"
            f"**{first_question_data['question']}**",
            view=view
        )
        view.message = message # Stocker le message pour pouvoir le modifier plus tard
    else:
        print(f"Erreur: Le salon d'onboarding (ID: {ONBOARDING_CHANNEL_ID}) est introuvable. Veuillez vérifier l'ID.")

# --- Lancement du bot ---
if __name__ == '__main__':
    # Vérifications pour s'assurer que les IDs ont été remplacés (sauf le token qui vient de l'env)
    if GUILD_ID == 0 or ONBOARDING_CHANNEL_ID == 0 or \
       ROLE_JOUEUR_PS3_ID == 0 or ROLE_MEMBRE_ID == 0: # J'ai mis 0 comme valeur par défaut pour les IDs non définis
        print("\n\nATTENTION: Veuillez vérifier que TOUS les IDs dans la section '--- Configuration ---' sont corrects et non à 0.\n\n")
    
    bot.run(TOKEN)
