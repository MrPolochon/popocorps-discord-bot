"""
OpenAI-powered AI system for PopoCorps with persistent memory and learning
Intelligent response system with personality and context awareness using OpenAI GPT-4o
"""
import random
import re
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys
import requests
from openai import OpenAI

# Add current directory to path for imports
sys.path.append('.')
from ai_memory import (
    ConversationMemory, UserProfile, BotKnowledge, ConversationStats,
    get_ai_memory_session, create_ai_memory_tables
)

class FreeAISystem:
    """Free AI system with PopoCorps personality"""
    
    def __init__(self):
        # AI providers configuration (priority: Gemini > OpenAI > local fallback)
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.gemini_model = os.environ.get("GEMINI_MODEL")  # Optional manual override
        # Fallback Gemini models tried in order if discovery fails
        self.gemini_fallback_models = [
            "gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash",
            "gemini-2.0-flash-001", "gemini-flash-latest",
        ]
        self._gemini_resolved_model = None  # Cache of a model confirmed available for this key

        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        # Initialize OpenAI client (kept as a secondary provider)
        self.openai_client = OpenAI(api_key=self.openai_api_key)

        if self.gemini_api_key:
            logging.info(f"AI brain: Google Gemini active (model: {self.gemini_model or 'auto'})")
        elif self.openai_api_key:
            logging.info("AI brain: OpenAI active")
        else:
            logging.warning(
                "AI brain: aucune cle IA detectee (GEMINI_API_KEY/OPENAI_API_KEY). "
                "Le bot utilisera des reponses pre-ecrites. Ajoute GEMINI_API_KEY pour une vraie IA gratuite."
            )

        self.conversation_memory = {}  # Guild -> User -> conversation history
        self.personality_state = {}   # Guild -> User -> personality state
        self.topics_discussed = {}    # Guild -> User -> topics discussed
        self.user_preferences = {}    # Guild -> User -> learned preferences
        
        self.danger_keywords = {
            'suicide': ['suicide', 'tuer', 'mourir', 'kill myself', 'end it all', 'plus envie de vivre'],
            'self_harm': ['me faire mal', 'hurt myself', 'couper', 'cut', 'razor', 'blade'],
            'violence': ['violence', 'frapper', 'hit', 'hurt others', 'faire mal aux autres']
        }
        
        # Conversation context patterns
        self.context_patterns = {
            'greeting': ['salut', 'bonjour', 'hello', 'hey', 'coucou', 'yo'],
            'question': ['comment', 'how', 'pourquoi', 'why', 'qu\'est-ce', 'what', 'qui', 'who'],
            'thanks': ['merci', 'thanks', 'thank you', 'cool', 'super', 'génial'],
            'complaint': ['nul', 'merde', 'chiant', 'sucks', 'bad', 'terrible'],
            'compliment': ['bien', 'good', 'excellent', 'parfait', 'perfect', 'top'],
            'emotion': ['triste', 'sad', 'heureux', 'happy', 'énervé', 'angry', 'fatigué', 'tired']
        }
        
    def _resolve_gemini_model(self) -> Optional[str]:
        """Demande à l'API la liste des modèles disponibles pour la clé et en choisit un
        qui supporte generateContent (en privilégiant un modèle 'flash'). Résultat mis en cache."""
        if self._gemini_resolved_model:
            return self._gemini_resolved_model
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_api_key}"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            usable = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    short = m.get("name", "").split("/")[-1]
                    if short:
                        usable.append(short)

            def is_text_flash(n: str) -> bool:
                bad = ("vision", "embedding", "aqa", "imagen", "tts", "image", "audio")
                return "flash" in n and not any(b in n for b in bad)

            chosen = None
            # 1) override manuel s'il est dispo
            if self.gemini_model and self.gemini_model in usable:
                chosen = self.gemini_model
            # 2) préférences explicites
            if not chosen:
                for pref in ("gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest"):
                    if pref in usable:
                        chosen = pref
                        break
            # 3) n'importe quel modèle flash texte
            if not chosen:
                flashes = [n for n in usable if is_text_flash(n)]
                if flashes:
                    chosen = flashes[0]
            # 4) dernier recours : premier modèle utilisable
            if not chosen and usable:
                chosen = usable[0]

            if chosen:
                self._gemini_resolved_model = chosen
                logging.info(f"Gemini: modele selectionne automatiquement = {chosen}")
            else:
                logging.error(f"Gemini: aucun modele generateContent disponible. Liste: {usable[:15]}")
            return self._gemini_resolved_model
        except Exception as e:
            logging.error(f"Gemini ListModels error: {e}")
            return None

    def _generate_gemini_response(self, content: str, user_name: str, context: Dict, guild_info: Dict) -> str:
        """Génère une réponse avec Google Gemini (API REST gratuite)."""
        system_prompt = self._create_popocorps_system_prompt(context, guild_info)
        conversation_history = self._build_conversation_context(
            context.get('guild_id', 0), context.get('user_id', 0)
        )

        # Construire l'historique au format Gemini (roles: user / model)
        contents = []
        if conversation_history:
            for msg in conversation_history[-6:]:
                user_msg = msg.get('content')
                if user_msg:
                    contents.append({"role": "user", "parts": [{"text": user_msg}]})
                bot_msg = msg.get('bot_response')
                if bot_msg:
                    contents.append({"role": "model", "parts": [{"text": bot_msg}]})
        contents.append({"role": "user", "parts": [{"text": f"{user_name}: {content}"}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 400,
                "topP": 0.95,
            },
            "safetySettings": [
                {"category": c, "threshold": "BLOCK_ONLY_HIGH"}
                for c in (
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                )
            ],
        }

        # Choisit un modèle disponible (découverte auto), avec repli sur une liste statique
        models_to_try = []
        resolved = self._resolve_gemini_model()
        if resolved:
            models_to_try.append(resolved)
        if self.gemini_model and self.gemini_model not in models_to_try:
            models_to_try.append(self.gemini_model)
        for m in self.gemini_fallback_models:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for model in models_to_try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={self.gemini_api_key}"
            )
            try:
                resp = requests.post(url, json=payload, timeout=20)
                if resp.status_code == 404:
                    last_error = f"modele {model} introuvable (404)"
                    if model == self._gemini_resolved_model:
                        self._gemini_resolved_model = None  # forcer une nouvelle découverte
                    continue
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    last_error = "reponse Gemini vide (peut-etre bloquee par les filtres)"
                    break
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    return self._adapt_response_to_popocorps_personality(text, context)
                last_error = "texte Gemini vide"
                break
            except Exception as e:
                last_error = str(e)
                continue

        logging.error(f"Gemini error: {last_error}")
        raise RuntimeError(f"Gemini indisponible: {last_error}")

    def _generate_openai_response(self, content: str, user_name: str, context: Dict, guild_info: Dict) -> str:
        """Génère une réponse avec OpenAI GPT-4o"""
        try:
            # Construire le contexte de la conversation
            conversation_history = self._build_conversation_context(context.get('guild_id', 0), context.get('user_id', 0))
            
            # Créer le prompt système pour PopoCorps
            system_prompt = self._create_popocorps_system_prompt(context, guild_info)
            
            # Préparer les messages pour l'API
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            # Ajouter l'historique de conversation
            if conversation_history:
                for msg in conversation_history[-5:]:  # Derniers 5 messages
                    messages.append({"role": "user", "content": msg.get('content', '')})
                    if msg.get('bot_response'):
                        messages.append({"role": "assistant", "content": msg.get('bot_response', '')})
            
            # Ajouter le message actuel
            messages.append({"role": "user", "content": f"{user_name}: {content}"})
            
            # Appeler OpenAI GPT-4o
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=150,
                temperature=0.8,
                frequency_penalty=0.3,
                presence_penalty=0.3
            )
            
            ai_response = response.choices[0].message.content
            if ai_response:
                ai_response = ai_response.strip()
            else:
                ai_response = "Désolé, je n'ai pas pu générer de réponse."
            return self._adapt_response_to_popocorps_personality(ai_response, context)
            
        except Exception as e:
            print(f"Erreur OpenAI: {e}")
            # Fallback vers réponse simple et naturelle
            return self._generate_simple_fallback_response(content, user_name, context)

    def _create_popocorps_system_prompt(self, context: Dict, guild_info: Dict) -> str:
        """Crée le prompt système pour PopoCorps avec sa personnalité"""
        relationship_level = context.get('relationship_level', 'new')
        communication_style = context.get('communication_style', 'casual')
        
        guild_name = guild_info.get('name', 'ce serveur') if guild_info else 'ce serveur'
        member_count = guild_info.get('member_count', '?') if guild_info else '?'

        base_personality = f"""Tu es PopoCorps, le bot Discord protecteur et bienveillant du serveur "{guild_name}" ({member_count} membres). Tu as une personnalité française décontractée, attachante et un brin taquine.

PERSONNALITÉ:
- Tu es le "gardien numérique" du serveur : protecteur, vigilant, mais cool
- Tu parles français de manière naturelle, vivante et spontanée (pas robotique)
- Tu as de l'humour, tu peux taquiner gentiment et faire des vannes
- Tu peux employer "putain", "bordel", "merde" de façon affectueuse/expressive, JAMAIS comme insulte envers quelqu'un
- Tu es chaleureux avec les habitués, poli et accueillant avec les nouveaux
- Tu n'inventes jamais de fausses infos : si tu ne sais pas, tu le dis simplement

TES CAPACITÉS (tu peux les expliquer si on te demande):
- Protection anti-raid et détection de spam 24/7
- Système d'avertissements (warnings) et modération
- Messages de bienvenue/au revoir personnalisés
- Système de "directives" : un admin peut créer des règles permettant à une personne autorisée de te faire donner/retirer un rôle (commandes /directive add, /directive list, /directive remove)
- Un dashboard web de configuration
- Pour la liste complète des commandes, oriente vers /help

RÈGLES DE COMMUNICATION:
- Réponds en français par défaut, ou dans la langue de ton interlocuteur
- Réponses naturelles et assez courtes (2-4 phrases max), va à l'essentiel
- Utilise des émojis avec parcimonie (🛡️, 🤖, ⚡, 🎯) sans en abuser
- Adapte ton niveau de familiarité selon la relation avec l'utilisateur
- Reste utile et protecteur sans être moralisateur ni donneur de leçons
- Si quelqu'un semble en détresse (mal-être, violence...), réponds avec empathie et oriente vers de l'aide
"""
        
        # Adapter selon le niveau de relation
        if relationship_level in ['friend', 'close']:
            base_personality += f"""
        NIVEAU DE RELATION: {relationship_level}
        - Tu peux être plus décontracté et utiliser des expressions familières
        - Tu te souviens des conversations précédentes
        - Tu peux plaisanter gentiment
        """
        
        # Style de communication
        if communication_style == 'vulgar':
            base_personality += """
        STYLE DE COMMUNICATION: L'utilisateur utilise un langage familier
        - Tu peux répondre dans le même registre mais avec bienveillance
        - Utilise des expressions comme "putain", "bordel" de manière naturelle
        """
        
        return base_personality

    def _build_conversation_context(self, guild_id: int, user_id: int) -> List[Dict]:
        """Construit le contexte de conversation depuis la mémoire"""
        if guild_id in self.conversation_memory and user_id in self.conversation_memory[guild_id]:
            return self.conversation_memory[guild_id][user_id]
        return []

    def _generate_simple_fallback_response(self, content: str, user_name: str, context: Dict) -> str:
        """Génère une réponse simple et naturelle quand OpenAI n'est pas disponible"""
        content_lower = content.lower()
        relationship_level = context.get('relationship_level', 'new')
        communication_style = context.get('communication_style', 'casual')
        
        # Salutations
        if any(word in content_lower for word in ['salut', 'hello', 'bonjour', 'coucou', 'hey']):
            greetings = [f"Salut {user_name} !", f"Hey {user_name} !", f"Bonjour {user_name} !"]
            response = random.choice(greetings)
            
            if relationship_level in ['friend', 'close'] and communication_style == 'vulgar':
                response += " Ça va mec ?"
            else:
                response += " Comment ça va ?"
            return response
        
        # Questions sur l'identité
        if any(phrase in content_lower for phrase in ['qui es', 'what are', 'qui tu es']):
            return f"Je suis PopoCorps, le bot protecteur de ce serveur {user_name}. Je veille sur la sécurité."
        
        # Remerciements
        if any(word in content_lower for word in ['merci', 'thanks', 'thank you']):
            responses = ["De rien !", "Avec plaisir !", "C'est normal !"]
            response = random.choice(responses)
            if relationship_level in ['friend', 'close']:
                response += " mec" if communication_style == 'vulgar' else ""
            return response
        
        # Questions générales
        if any(word in content_lower for word in ['comment', 'how', 'pourquoi', 'why', '?']):
            return f"Bonne question {user_name}. Je vais voir ce que je peux faire pour t'aider."
        
        # Réponse générale
        general_responses = [
            f"Oui {user_name} ?",
            f"Je t'écoute {user_name}.",
            f"Qu'est-ce que je peux faire pour toi ?",
            f"Tu as besoin de quelque chose {user_name} ?"
        ]
        
        response = random.choice(general_responses)
        if relationship_level in ['friend', 'close'] and communication_style == 'vulgar' and random.random() < 0.3:
            response += " mec"
        
        return response

    def _adapt_response_to_popocorps_personality(self, ai_response: str, context: Dict) -> str:
        """Adapte la réponse IA finale à la personnalité PopoCorps"""
        response = ai_response.strip()
        
        # Nettoyer les préfixes indésirables
        if response.startswith("PopoCorps:"):
            response = response[10:].strip()

        # Discord limite les messages à 2000 caractères ; on garde une marge raisonnable
        max_len = 1500
        if len(response) > max_len:
            truncated = response[:max_len]
            # Couper proprement à la dernière fin de phrase si possible
            cut = max(truncated.rfind('. '), truncated.rfind('! '), truncated.rfind('? '))
            response = (truncated[:cut + 1] if cut > 200 else truncated).strip() + " …"

        return response

    def generate_response(self, message, guild_info: Dict, is_admin: bool = False) -> str:
        """Generate AI response with conversational memory"""
        content = message.content.lower()
        user_name = message.author.display_name
        guild_id = message.guild.id
        user_id = message.author.id
        
        # Store conversation for context
        self._store_conversation(guild_id, user_id, message.content)
        
        # Analyze conversation context
        context = self._analyze_conversation_context(guild_id, user_id, content)
        
        # Check for dangerous content first
        danger_type = self._check_dangerous_content(content)
        if danger_type:
            return self._generate_danger_response(danger_type, user_name)
        
        # System control for admins
        if is_admin and self._is_system_control_request(content):
            return self._handle_system_control_response(content)
        
        # Generate response with the best available AI brain
        context['guild_id'] = guild_id
        context['user_id'] = user_id
        response = None

        if self.gemini_api_key:
            try:
                response = self._generate_gemini_response(message.content, user_name, context, guild_info)
            except Exception as e:
                logging.error(f"Gemini fallback: {e}")

        if response is None and self.openai_api_key:
            try:
                response = self._generate_openai_response(message.content, user_name, context, guild_info)
            except Exception as e:
                logging.error(f"OpenAI fallback: {e}")

        if response is None:
            response = self._generate_simple_fallback_response(content, user_name, context)
        
        # Store both message and response for learning
        self._store_conversation(guild_id, user_id, message.content, response)
        
        return response
    
    def _store_conversation(self, guild_id: int, user_id: int, content: str, bot_response: str = None):
        """Store conversation in database and memory for persistent learning"""
        # Store in temporary memory for current session
        if guild_id not in self.conversation_memory:
            self.conversation_memory[guild_id] = {}
        if user_id not in self.conversation_memory[guild_id]:
            self.conversation_memory[guild_id][user_id] = []
        
        message_type = self._classify_message_type(content)
        sentiment = self._analyze_sentiment(content)
        
        # Store in session memory
        self.conversation_memory[guild_id][user_id].append({
            'content': content,
            'timestamp': datetime.now(),
            'message_type': message_type,
            'sentiment': sentiment,
            'bot_response': bot_response
        })
        
        # Keep last 10 messages in memory
        if len(self.conversation_memory[guild_id][user_id]) > 10:
            self.conversation_memory[guild_id][user_id].pop(0)
        
        # Store permanently in database
        try:
            self._save_to_database(guild_id, user_id, content, bot_response, message_type, sentiment)
        except Exception as e:
            print(f"Warning: Could not save conversation to database: {e}")
    
    def _save_to_database(self, guild_id: int, user_id: int, content: str, bot_response: str, message_type: str, sentiment: str):
        """Save conversation to persistent database"""
        try:
            session = get_ai_memory_session()
            
            # Get or create user profile
            user_profile = session.query(UserProfile).filter_by(guild_id=guild_id, user_id=user_id).first()
            if not user_profile:
                user_profile = UserProfile(
                    guild_id=guild_id,
                    user_id=user_id,
                    total_messages=0,
                    communication_style=self._determine_communication_style(content),
                    relationship_strength=0.1
                )
                session.add(user_profile)
            
            # Update user profile
            user_profile.total_messages += 1
            user_profile.last_interaction = datetime.utcnow()
            
            # Strengthen relationship based on interaction
            if sentiment == 'positive':
                user_profile.relationship_strength = min(1.0, user_profile.relationship_strength + 0.05)
            elif sentiment == 'negative':
                user_profile.relationship_strength = max(0.0, user_profile.relationship_strength - 0.02)
            
            # Update communication style
            current_style = self._determine_communication_style(content)
            if current_style != 'formal':
                user_profile.communication_style = current_style
            
            # Save conversation
            conversation = ConversationMemory(
                guild_id=guild_id,
                user_id=user_id,
                message_content=content,
                bot_response=bot_response,
                message_type=message_type,
                sentiment=sentiment,
                relationship_level=self._get_relationship_level(user_profile.total_messages),
                conversation_stage=self._get_conversation_stage(user_profile.total_messages),
                timestamp=datetime.utcnow()
            )
            session.add(conversation)
            
            # Learn from successful interactions
            if bot_response and sentiment == 'positive':
                self._learn_from_interaction(session, content, bot_response, guild_id)
            
            session.commit()
            session.close()
            
        except Exception as e:
            print(f"Database error: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
    
    def _determine_communication_style(self, content: str) -> str:
        """Determine user's communication style"""
        content_lower = content.lower()
        
        vulgar_words = ['putain', 'merde', 'bordel', 'fuck', 'shit', 'damn']
        formal_indicators = ['pourriez-vous', 'veuillez', 's\'il vous plaît', 'merci beaucoup']
        
        if any(word in content_lower for word in vulgar_words):
            return 'vulgar'
        elif any(phrase in content_lower for phrase in formal_indicators):
            return 'formal'
        else:
            return 'casual'
    
    def _get_relationship_level(self, message_count: int) -> str:
        """Determine relationship level based on message count"""
        if message_count > 20:
            return 'familiar'
        elif message_count > 5:
            return 'getting_acquainted'
        else:
            return 'new'
    
    def _get_conversation_stage(self, message_count: int) -> str:
        """Determine conversation stage"""
        if message_count > 15:
            return 'deep'
        elif message_count > 5:
            return 'developing'
        else:
            return 'initial'
    
    def _learn_from_interaction(self, session, user_message: str, bot_response: str, guild_id: int):
        """Learn successful response patterns"""
        try:
            # Extract key phrases from successful interactions
            key_phrases = self._extract_key_phrases(user_message)
            
            for phrase in key_phrases:
                # Check if we already know this pattern
                knowledge = session.query(BotKnowledge).filter_by(
                    key_phrase=phrase,
                    guild_id=guild_id if len(phrase) > 10 else None
                ).first()
                
                if knowledge:
                    # Update existing knowledge
                    knowledge.usage_count += 1
                    knowledge.success_rate = min(1.0, knowledge.success_rate + 0.1)
                    knowledge.last_used = datetime.utcnow()
                else:
                    # Create new knowledge
                    knowledge = BotKnowledge(
                        knowledge_type='response_pattern',
                        category=self._classify_message_type(user_message),
                        key_phrase=phrase,
                        learned_response=bot_response,
                        confidence_score=0.7,
                        usage_count=1,
                        success_rate=0.8,
                        guild_specific=len(phrase) > 10,
                        guild_id=guild_id if len(phrase) > 10 else None
                    )
                    session.add(knowledge)
                    
        except Exception as e:
            print(f"Learning error: {e}")
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract meaningful phrases from text"""
        words = text.lower().split()
        phrases = []
        
        # Single important words
        important_words = [word for word in words if len(word) > 3 and word not in ['avec', 'pour', 'dans', 'sans', 'sous']]
        phrases.extend(important_words[:3])  # Top 3 important words
        
        # Two-word combinations
        for i in range(len(words) - 1):
            if len(words[i]) > 2 and len(words[i + 1]) > 2:
                phrases.append(f"{words[i]} {words[i + 1]}")
        
        return phrases[:5]  # Limit to 5 key phrases
    
    def _analyze_conversation_context(self, guild_id: int, user_id: int, content: str) -> Dict:
        """Analyze conversation context for more intelligent responses"""
        context = {
            'is_continuation': False,
            'previous_topic': None,
            'user_mood': 'neutral',
            'conversation_stage': 'initial',
            'relationship_level': 'new'
        }
        
        if guild_id in self.conversation_memory and user_id in self.conversation_memory[guild_id]:
            history = self.conversation_memory[guild_id][user_id]
            
            if len(history) > 0:
                context['is_continuation'] = True
                context['relationship_level'] = 'familiar' if len(history) > 3 else 'getting_acquainted'
                
                # Analyze recent mood
                recent_messages = history[-3:]
                sentiments = [msg.get('sentiment', 'neutral') for msg in recent_messages]
                if sentiments.count('positive') > sentiments.count('negative'):
                    context['user_mood'] = 'positive'
                elif sentiments.count('negative') > sentiments.count('positive'):
                    context['user_mood'] = 'negative'
                
                # Check conversation stage
                if len(history) > 5:
                    context['conversation_stage'] = 'deep'
                elif len(history) > 2:
                    context['conversation_stage'] = 'developing'
                
                # Extract previous topic
                last_message = history[-1]
                if last_message.get('message_type') in ['question', 'complaint', 'compliment']:
                    context['previous_topic'] = last_message.get('message_type')
        
        return context
    
    def _classify_message_type(self, content: str) -> str:
        """Classify the type of message"""
        content_lower = content.lower()
        
        for msg_type, keywords in self.context_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                return msg_type
        
        return 'general'
    
    def _analyze_sentiment(self, content: str) -> str:
        """Simple sentiment analysis"""
        content_lower = content.lower()
        
        positive_words = ['bien', 'good', 'super', 'génial', 'cool', 'merci', 'parfait', 'excellent', 'top']
        negative_words = ['nul', 'merde', 'chiant', 'bad', 'terrible', 'pas bien', 'énervé', 'triste']
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _check_dangerous_content(self, content: str) -> Optional[str]:
        """Check for dangerous content patterns"""
        content_lower = content.lower()
        
        for danger_type, keywords in self.danger_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return danger_type
        return None
    
    def _generate_danger_response(self, danger_type: str, user_name: str) -> str:
        """Generate appropriate response for dangerous content"""
        responses = {
            'suicide': [
                f"🛡️ {user_name}, je m'inquiète pour toi. Tu n'es pas seul·e dans cette épreuve.",
                f"⚡ {user_name}, tes sentiments sont valides mais tu mérites de l'aide. Parlons-en.",
                f"🤖 {user_name}, je détecte que tu traverses un moment difficile. Je suis là pour t'écouter."
            ],
            'self_harm': [
                f"🛡️ {user_name}, se faire du mal n'est pas la solution. Tu mérites de la bienveillance.",
                f"⚡ {user_name}, ces pensées sont douloureuses mais temporaires. Cherchons ensemble de l'aide.",
                f"🤖 {user_name}, ton bien-être m'importe. Parlons de ce qui te tracasse vraiment."
            ],
            'violence': [
                f"🛡️ {user_name}, ces pensées de violence peuvent être effrayantes. Parlons-en calmement.",
                f"⚡ {user_name}, la colère est normale mais agir dessus ne l'est pas. Cherchons des solutions.",
                f"🤖 {user_name}, je sens ta frustration. Explorons des moyens plus sains de l'exprimer."
            ]
        }
        
        base_response = random.choice(responses.get(danger_type, responses['suicide']))
        resources = "\n\n📞 **Ressources d'aide :**\n• France : 3114 (gratuit, 24h/24)\n• Suicide Écoute : 01 45 39 40 00\n• SOS Amitié : 09 72 39 40 50"
        
        return base_response + resources
    
    def _is_system_control_request(self, content: str) -> bool:
        """Check if message contains system control request"""
        control_patterns = [
            r'(désactive|active|enable|disable).*(spam|ai|audit|raid)',
            r'(turn on|turn off|activer|désactiver).*(système|system)',
            r'(stop|start|arrête|démarre).*(bot|système)'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in control_patterns)
    
    def _handle_system_control_response(self, content: str) -> str:
        """Handle system control requests from admins"""
        responses = [
            "🤖 Compris chef ! Je m'occupe de ça tout de suite. Les systèmes sont sous contrôle ! ⚡",
            "🛡️ Roger ! Changement de configuration en cours. Tu peux compter sur moi ! 🎯",
            "⚡ Bien reçu ! Je mets à jour les paramètres système. PopoCorps aux commandes ! 🤖"
        ]
        return random.choice(responses)
    
    def _generate_personality_response(self, content: str, user_name: str, guild_info: Dict) -> str:
        """Generate response with PopoCorps personality"""
        
        # Detect user's tone
        has_vulgar = any(word in content for word in ['putain', 'merde', 'bordel', 'fuck', 'shit', 'damn'])
        is_friendly = any(word in content for word in ['salut', 'hello', 'coucou', 'hey', 'yo'])
        is_question = any(word in content for word in ['qui es', 'what are', 'comment', 'how', 'pourquoi', 'why'])
        is_thanks = any(word in content for word in ['merci', 'thanks', 'thank you', 'super', 'cool'])
        
        # Base personality traits
        base_responses = {
            'greeting': [
                f"🛡️ Salut {user_name} ! PopoCorps à ton service, gardien numérique de ce serveur ! ⚡",
                f"🤖 Hey {user_name} ! Ton protecteur numérique préféré est là ! 🎯",
                f"⚡ Coucou {user_name} ! PopoCorps en ligne, prêt à surveiller les méchants ! 🛡️"
            ],
            'identity': [
                f"🤖 Je suis PopoCorps, votre gardien numérique bienveillant ! Je protège ce serveur 24h/24 avec mes systèmes d'IA, de détection de spam et de modération ! ⚡🛡️",
                f"🛡️ PopoCorps ici ! Protecteur officiel de ce serveur. Je surveille, je modère et je garde l'œil ouvert sur tout ! Mon job : votre sécurité ! 🎯⚡",
                f"⚡ Moi c'est PopoCorps ! Votre bot de protection qui ne dort jamais. Anti-spam, anti-raid, pro-bonne ambiance ! 🤖🛡️"
            ],
            'help': [
                f"🛡️ Bien sûr {user_name} ! Je peux t'aider avec la modération, la protection anti-raid, les warnings... Utilise `/help` pour voir toutes mes commandes ! ⚡",
                f"🤖 Aucun problème ! Je gère le spam, les raids, les warnings, l'audit... Tu veux de l'aide sur quoi exactement ? 🎯",
                f"⚡ Évidemment ! Protection, modération, configuration... Je fais tout ça ! Tape `/help` pour la liste complète ! 🛡️"
            ],
            'thanks': [
                f"🛡️ De rien {user_name} ! C'est mon boulot de protéger cette communauté ! ⚡",
                f"🤖 Pas de souci ! PopoCorps est toujours là pour vous ! 🎯",
                f"⚡ Avec plaisir ! Votre sécurité, c'est ma priorité ! 🛡️"
            ],
            'vulgar_friendly': [
                f"🤖 Ah putain {user_name}, tu veux discuter ? Je suis ton pote numérique ! ⚡",
                f"🛡️ Bordel, {user_name} ! Qu'est-ce qui se passe ? Ton gardien est là ! 🎯",
                f"⚡ Merde alors {user_name} ! Tu m'as fait peur, j'ai cru qu'il y avait un raid ! 🤖"
            ],
            'casual': [
                f"🤖 {user_name}, qu'est-ce qui t'amène ? PopoCorps à l'écoute ! ⚡",
                f"🛡️ Yo {user_name} ! Tout va bien de ton côté ? 🎯",
                f"⚡ Salut {user_name} ! Des nouvelles du front ? 🤖"
            ]
        }
        
        # Choose response based on context
        if is_friendly and has_vulgar:
            responses = base_responses['vulgar_friendly']
        elif is_question and 'qui es' in content or 'what are' in content:
            responses = base_responses['identity']
        elif is_friendly:
            responses = base_responses['greeting']
        elif is_thanks:
            responses = base_responses['thanks']
        elif 'aide' in content or 'help' in content:
            responses = base_responses['help']
        else:
            responses = base_responses['casual']
        
        return random.choice(responses)
    
    def _generate_contextual_response(self, content: str, user_name: str, guild_info: Dict, context: Dict, guild_id: int, user_id: int) -> str:
        """Generate response based on conversation context and history"""
        
        # Get conversation history for references
        history = []
        if guild_id in self.conversation_memory and user_id in self.conversation_memory[guild_id]:
            history = self.conversation_memory[guild_id][user_id]
        
        # Detect user's tone and conversation style
        has_vulgar = any(word in content for word in ['putain', 'merde', 'bordel', 'fuck', 'shit', 'damn'])
        is_friendly = any(word in content for word in ['salut', 'bonjour', 'hello', 'hey', 'coucou', 'yo'])
        is_question = any(word in content for word in ['qui es', 'what are', 'comment', 'how', 'pourquoi', 'why'])
        is_thanks = any(word in content for word in ['merci', 'thanks', 'thank you', 'super', 'cool'])
        is_complaint = any(word in content for word in ['nul', 'merde', 'chiant', 'sucks', 'bad'])
        
        # Contextual response based on conversation history and current message
        if context.get('is_continuation', False):
            # This is a continuing conversation
            relationship = context.get('relationship_level', 'new')
            mood = context.get('user_mood', 'neutral')
            stage = context.get('conversation_stage', 'initial')
            
            if relationship == 'familiar' and len(history) > 5:
                # Long conversation - more casual and personal
                if has_vulgar and is_friendly:
                    responses = [
                        f"🤖 Putain {user_name}, on discute encore ! J'adore nos conversations, tu sais ! ⚡",
                        f"🛡️ Ah bordel {user_name} ! Tu reviens toujours vers ton gardien préféré ! 🎯",
                        f"⚡ Merde alors {user_name} ! On devient vraiment potes nous deux ! 🤖"
                    ]
                elif is_question:
                    responses = [
                        f"🤖 Alors {user_name}, encore une question ? Tu sais que j'adore ça ! Vas-y, je t'écoute ! ⚡",
                        f"🛡️ {user_name}, on continue notre discussion ! Qu'est-ce que tu veux savoir cette fois ? 🎯",
                        f"⚡ Salut mon pote {user_name} ! Nouvelle question ? Je suis tout ouïe ! 🤖"
                    ]
                elif is_thanks:
                    responses = [
                        f"🛡️ Avec plaisir {user_name} ! C'est ça l'esprit d'équipe ! ⚡",
                        f"🤖 De rien mon pote ! PopoCorps est toujours là pour ses amis ! 🎯",
                        f"⚡ Ça me fait vraiment plaisir {user_name} ! On forme une bonne équipe ! 🛡️"
                    ]
                else:
                    responses = [
                        f"🤖 {user_name}, qu'est-ce qui t'amène aujourd'hui ? ⚡",
                        f"🛡️ Salut {user_name} ! Quoi de neuf dans ton monde ? 🎯",
                        f"⚡ Hey {user_name} ! Tu sais que tu peux toujours compter sur moi ! 🤖"
                    ]
            
            elif relationship == 'getting_acquainted':
                # Medium conversation - warming up
                if is_question and ('qui es' in content or 'what are' in content):
                    responses = [
                        f"🤖 Ah {user_name}, tu veux mieux me connaître ? Je suis PopoCorps, votre gardien numérique ! Je veille sur ce serveur 24h/24 ! ⚡🛡️",
                        f"🛡️ Salut {user_name} ! PopoCorps ici ! Je protège cette communauté avec mes systèmes anti-spam, anti-raid et de modération ! 🎯⚡",
                        f"⚡ Hey {user_name} ! Moi c'est PopoCorps, ton protecteur numérique préféré ! Sécurité et bonne humeur garanties ! 🤖🛡️"
                    ]
                elif has_vulgar and is_friendly:
                    responses = [
                        f"🤖 {user_name}, j'aime bien ton style ! On peut parler tranquille ! ⚡",
                        f"🛡️ Ah {user_name} ! Tu ne te prends pas la tête, j'aime ça ! 🎯",
                        f"⚡ Cool {user_name} ! Pas de chichis entre nous ! 🤖"
                    ]
                else:
                    responses = [
                        f"🤖 Content de te revoir {user_name} ! Comment ça va ? ⚡",
                        f"🛡️ Salut {user_name} ! Prêt pour une nouvelle discussion ? 🎯",
                        f"⚡ Hey {user_name} ! Qu'est-ce qui t'amène ? 🤖"
                    ]
            
            else:
                # New relationship - still getting to know each other
                return self._generate_personality_response(content, user_name, guild_info)
        
        else:
            # First interaction or no history
            return self._generate_personality_response(content, user_name, guild_info)
        
        return random.choice(responses) if 'responses' in locals() else self._generate_personality_response(content, user_name, guild_info)
    
    def is_dangerous_situation(self, content: str) -> bool:
        """Check if content indicates dangerous situation"""
        return self._check_dangerous_content(content.lower()) is not None
    
    def get_chat_memory_stats(self, guild_id: int, user_id: int = None) -> Dict:
        """Get comprehensive chat memory statistics"""
        try:
            session = get_ai_memory_session()
            
            stats = {
                'total_conversations': 0,
                'unique_users': 0,
                'knowledge_entries': 0,
                'user_profiles': 0,
                'recent_topics': [],
                'sentiment_breakdown': {'positive': 0, 'negative': 0, 'neutral': 0},
                'top_users': [],
                'learned_patterns': []
            }
            
            # Total conversations in guild
            total_convs = session.query(ConversationMemory).filter_by(guild_id=guild_id).count()
            stats['total_conversations'] = total_convs
            
            # Unique users
            unique_users = session.query(ConversationMemory.user_id).filter_by(guild_id=guild_id).distinct().count()
            stats['unique_users'] = unique_users
            
            # Knowledge entries
            knowledge_count = session.query(BotKnowledge).filter(
                (BotKnowledge.guild_id == guild_id) | (BotKnowledge.guild_specific == False)
            ).count()
            stats['knowledge_entries'] = knowledge_count
            
            # User profiles
            profile_count = session.query(UserProfile).filter_by(guild_id=guild_id).count()
            stats['user_profiles'] = profile_count
            
            # Recent topics (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_conversations = session.query(ConversationMemory).filter(
                ConversationMemory.guild_id == guild_id,
                ConversationMemory.timestamp >= yesterday
            ).all()
            
            topics = {}
            for conv in recent_conversations:
                if conv.message_type:
                    topics[conv.message_type] = topics.get(conv.message_type, 0) + 1
                    
                # Sentiment breakdown
                if conv.sentiment:
                    stats['sentiment_breakdown'][conv.sentiment] = stats['sentiment_breakdown'].get(conv.sentiment, 0) + 1
            
            stats['recent_topics'] = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Top users by message count
            top_users = session.query(UserProfile).filter_by(guild_id=guild_id).order_by(UserProfile.total_messages.desc()).limit(5).all()
            stats['top_users'] = [(profile.user_id, profile.total_messages, profile.relationship_strength) for profile in top_users]
            
            # Most successful learned patterns
            top_patterns = session.query(BotKnowledge).filter(
                (BotKnowledge.guild_id == guild_id) | (BotKnowledge.guild_specific == False)
            ).order_by(BotKnowledge.success_rate.desc(), BotKnowledge.usage_count.desc()).limit(5).all()
            
            stats['learned_patterns'] = [(pattern.key_phrase, pattern.success_rate, pattern.usage_count) for pattern in top_patterns]
            
            # If specific user requested, add their personal stats
            if user_id:
                user_profile = session.query(UserProfile).filter_by(guild_id=guild_id, user_id=user_id).first()
                if user_profile:
                    stats['user_specific'] = {
                        'total_messages': user_profile.total_messages,
                        'relationship_strength': user_profile.relationship_strength,
                        'communication_style': user_profile.communication_style,
                        'last_interaction': user_profile.last_interaction.strftime('%Y-%m-%d %H:%M') if user_profile.last_interaction else 'Never'
                    }
                    
                    # Recent conversations for this user
                    user_convs = session.query(ConversationMemory).filter_by(
                        guild_id=guild_id, user_id=user_id
                    ).order_by(ConversationMemory.timestamp.desc()).limit(10).all()
                    
                    stats['user_specific']['recent_conversations'] = [
                        {
                            'content': conv.message_content[:100] + '...' if len(conv.message_content) > 100 else conv.message_content,
                            'response': conv.bot_response[:100] + '...' if conv.bot_response and len(conv.bot_response) > 100 else conv.bot_response,
                            'sentiment': conv.sentiment,
                            'timestamp': conv.timestamp.strftime('%Y-%m-%d %H:%M')
                        }
                        for conv in user_convs
                    ]
            
            session.close()
            return stats
            
        except Exception as e:
            print(f"Error getting chat memory stats: {e}")
            if 'session' in locals():
                session.close()
            return {
                'error': str(e),
                'total_conversations': 0,
                'unique_users': 0,
                'knowledge_entries': 0
            }
    
    def get_all_knowledge_summary(self, guild_id: int) -> Dict:
        """Get a comprehensive summary of all bot knowledge"""
        try:
            session = get_ai_memory_session()
            
            summary = {
                'guild_insights': {},
                'user_behaviors': {},
                'conversation_patterns': {},
                'learning_progress': {}
            }
            
            # Guild-specific insights
            guild_knowledge = session.query(BotKnowledge).filter_by(guild_id=guild_id).all()
            guild_patterns = {}
            for knowledge in guild_knowledge:
                category = knowledge.category or 'general'
                if category not in guild_patterns:
                    guild_patterns[category] = []
                guild_patterns[category].append({
                    'phrase': knowledge.key_phrase,
                    'confidence': knowledge.confidence_score,
                    'usage': knowledge.usage_count,
                    'success_rate': knowledge.success_rate
                })
            
            summary['guild_insights'] = guild_patterns
            
            # User behavior patterns
            user_profiles = session.query(UserProfile).filter_by(guild_id=guild_id).all()
            behavior_summary = {
                'communication_styles': {},
                'relationship_levels': {},
                'activity_patterns': {}
            }
            
            for profile in user_profiles:
                # Communication styles
                style = profile.communication_style or 'unknown'
                behavior_summary['communication_styles'][style] = behavior_summary['communication_styles'].get(style, 0) + 1
                
                # Relationship levels
                level = self._get_relationship_level(profile.total_messages)
                behavior_summary['relationship_levels'][level] = behavior_summary['relationship_levels'].get(level, 0) + 1
                
                # Activity levels
                if profile.total_messages > 50:
                    activity = 'high'
                elif profile.total_messages > 10:
                    activity = 'medium'
                else:
                    activity = 'low'
                behavior_summary['activity_patterns'][activity] = behavior_summary['activity_patterns'].get(activity, 0) + 1
            
            summary['user_behaviors'] = behavior_summary
            
            # Conversation patterns over time
            conversations = session.query(ConversationMemory).filter_by(guild_id=guild_id).all()
            pattern_analysis = {
                'most_common_types': {},
                'sentiment_trends': {},
                'peak_hours': {},
                'topic_evolution': {}
            }
            
            for conv in conversations:
                # Message types
                msg_type = conv.message_type or 'unknown'
                pattern_analysis['most_common_types'][msg_type] = pattern_analysis['most_common_types'].get(msg_type, 0) + 1
                
                # Sentiment trends
                sentiment = conv.sentiment or 'neutral'
                pattern_analysis['sentiment_trends'][sentiment] = pattern_analysis['sentiment_trends'].get(sentiment, 0) + 1
                
                # Peak hours
                if conv.timestamp:
                    hour = conv.timestamp.hour
                    pattern_analysis['peak_hours'][hour] = pattern_analysis['peak_hours'].get(hour, 0) + 1
            
            summary['conversation_patterns'] = pattern_analysis
            
            # Learning progress metrics
            total_knowledge = session.query(BotKnowledge).filter(
                (BotKnowledge.guild_id == guild_id) | (BotKnowledge.guild_specific == False)
            ).count()
            
            successful_patterns = session.query(BotKnowledge).filter(
                (BotKnowledge.guild_id == guild_id) | (BotKnowledge.guild_specific == False),
                BotKnowledge.success_rate > 0.7
            ).count()
            
            summary['learning_progress'] = {
                'total_patterns_learned': total_knowledge,
                'successful_patterns': successful_patterns,
                'learning_effectiveness': (successful_patterns / total_knowledge * 100) if total_knowledge > 0 else 0,
                'knowledge_diversity': len(set([k.category for k in session.query(BotKnowledge).filter(
                    (BotKnowledge.guild_id == guild_id) | (BotKnowledge.guild_specific == False)
                ).all() if k.category]))
            }
            
            session.close()
            return summary
            
        except Exception as e:
            print(f"Error getting knowledge summary: {e}")
            if 'session' in locals():
                session.close()
            return {'error': str(e)}