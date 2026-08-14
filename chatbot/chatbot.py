#!/usr/bin/env python3
"""
Chatbot de Seguros (Ollama + Fallback)
Arquivo: chatbot.py

Requisitos:
    pip install requests

Uso:
    1) Rode o Ollama: `ollama serve`
    2) Rode este script: `python chatbot_seguros.py`
"""

import requests
import json
import time
from typing import Optional

class OllamaChatbotSeguros:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.historico = []  # lista de dicts {"role": "usuario|bot", "text": "..."}
        # Dados de seguros (fonte única)
        self.seguros_info = {
            "vida": {
                "preco": "R$ 89,90/mês",
                "cobertura": ["Morte acidental", "Invalidez permanente", "Despesas médicas", "Assistência funeral"],
                "descricao": "Proteção para você e sua família contra imprevistos"
            },
            "automovel": {
                "preco": "R$ 199,90/mês",
                "cobertura": ["Colisão", "Roubo/Furto", "Incêndio", "Danos a terceiros", "Assistência 24h"],
                "descricao": "Cobertura completa para carros e motocicletas"
            },
            "residencial": {
                "preco": "R$ 129,90/mês",
                "cobertura": ["Incêndio", "Roubo", "Danos elétricos", "Vendaval", "Queda de raio"],
                "descricao": "Proteção para sua casa e patrimônio"
            },
            "motocicleta": {
                "preco": "R$ 159,90/mês",
                "cobertura": ["Colisão", "Roubo/Furto", "Incêndio", "Danos a terceiros", "Assistência 24h"],
                "descricao": "Cobertura especial para motos"
            },
            "eletrodomesticos": {
                "preco": "R$ 39,90/mês",
                "cobertura": ["Quebra acidental", "Defeitos elétricos", "Conserto técnico", "Assistência"],
                "descricao": "Proteção para seus eletrodomésticos"
            }
        }

        # Sinônimos rápidos para checagem heurística (previne chamadas desnecessárias ao modelo)
        self.sinonimos = {
            "vida": ["vida", "morte", "invalidez", "seguro de vida"],
            "automovel": ["carro", "automóvel", "veículo"],
            "motocicleta": ["moto", "motocicleta", "harley", "cg", "yamaha", "honda"],
            "residencial": ["casa", "apartamento", "imóvel", "residencial"],
            "eletrodomesticos": ["lavadora", "máquina de lavar", "geladeira", "micro-ondas", "televisão", "eletrodoméstico"]
        }

        # Para gerenciamento simples de "sim"/"não" após perguntas do bot
        self.ultimo_assunto = None  # ex: "contratar_vida", "info_eletro", etc.

    # -------------------------
    # Comunicacao com Ollama
    # -------------------------
    def verificar_conexao_ollama(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=8)
            return resp.status_code == 200
        except Exception:
            return False

    def gerar_resposta(self, prompt: str, system: Optional[str] = None, timeout: int = 60) -> str:
        """
        Chama /api/generate do Ollama. Faz parsing robusto para o caso do retorno em múltiplas linhas.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.9}
        }
        try:
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=timeout)
        except Exception as e:
            return f"Erro de conexão com Ollama: {e}"

        if resp.status_code != 200:
            return f"Erro na geração (status {resp.status_code})"

        text = resp.text.strip()
        if not text:
            return ""

        # Em algumas versões a API retorna múltiplas linhas (streaming). Pegamos a última linha JSON válida.
        linhas = text.splitlines()
        last = linhas[-1]
        try:
            data = json.loads(last)
            # chaves possíveis: "response", "text", "result" (varia entre versões)
            if isinstance(data, dict):
                return (data.get("response") or data.get("text") or data.get("result") or "").strip()
        except json.JSONDecodeError:
            # tenta decodificar o corpo inteiro
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return (data.get("response") or data.get("text") or data.get("result") or "").strip()
            except Exception:
                # fallback: devolver todo o body como string
                return text

        return ""

    # -------------------------
    # Heurísticas e classificação
    # -------------------------
    def _detecta_por_sinonimos(self, mensagem: str) -> Optional[str]:
        m = mensagem.lower()
        for chave, termos in self.sinonimos.items():
            for t in termos:
                if t in m:
                    return chave
        return None

    def classificar_intencao(self, mensagem: str) -> str:
        """
        Usa heurística rápida + chamada ao modelo para classificar intenção.
        Retorna uma das categorias:
            preco_seguro_vida, preco_seguro_carro, preco_seguro_residencial,
            preco_seguro_eletrodomesticos, preco_seguro_motocicleta,
            cobertura, lista_seguros, saudacao, despedida, outro
        """
        # Heurística local
        detect = self._detecta_por_sinonimos(mensagem)
        if detect == "vida":
            return "preco_seguro_vida"
        if detect == "automovel":
            return "preco_seguro_carro"
        if detect == "motocicleta":
            return "preco_seguro_motocicleta"
        if detect == "residencial":
            return "preco_seguro_residencial"
        if detect == "eletrodomesticos":
            return "preco_seguro_eletrodomesticos"

        # Prompt rígido para o modelo
        prompt = f"""
Você é um classificador de intenções para um chatbot de seguros.
Responda SOMENTE com UMA das categorias válidas (SEM pontuação, SEM explicações extras):

preco_seguro_vida
preco_seguro_carro
preco_seguro_residencial
preco_seguro_eletrodomesticos
preco_seguro_motocicleta
cobertura
lista_seguros
saudacao
despedida
outro

Mensagem: \"\"\"{mensagem}\"\"\"
"""
        resposta = self.gerar_resposta(prompt)
        cat = resposta.strip().lower()
        # normalizações simples
        replacements = {
            "preço": "preco",
            "preço_seguro_vida": "preco_seguro_vida",
            "preco_seguro_carro": "preco_seguro_carro",
            "automovel": "preco_seguro_carro",
            "moto": "preco_seguro_motocicleta",
        }
        for k, v in replacements.items():
            if k in cat:
                return v
        # se o modelo devolveu algo estranho, fallback para 'outro'
        validas = {
            "preco_seguro_vida", "preco_seguro_carro", "preco_seguro_residencial",
            "preco_seguro_eletrodomesticos", "preco_seguro_motocicleta",
            "cobertura", "lista_seguros", "saudacao", "despedida", "outro"
        }
        if cat in validas:
            return cat
        return "outro"

    # -------------------------
    # Respostas / handlers
    # -------------------------
    def _responder_saudacao(self) -> str:
        return ("🤖 Olá! Sou seu assistente virtual de seguros. Posso ajudar com:\n"
                "• Preços de seguros (Vida, Residencial, Automóvel/Motocicleta)\n"
                "• Coberturas\n"
                "• Tipos de seguros disponíveis\n\nComo posso ajudar você hoje?")

    def _responder_despedida(self) -> str:
        return "🤖 Obrigado por conversar! Volte sempre que precisar de informações sobre seguros. 👋"

    def _listar_seguros(self) -> str:
        s = "📋 Seguros disponíveis:\n"
        for k, v in self.seguros_info.items():
            s += f"• {k.title()}: {v['descricao']}\n"
        s += "\n💬 Pergunte sobre preços ou coberturas específicas!"
        return s

    def _fornecer_preco(self, tipo: str) -> str:
        info = self.seguros_info.get(tipo)
        if not info:
            return "❌ Desculpe, não encontrei informações sobre esse tipo de seguro."
        cov = "\n   ◦ ".join(info["cobertura"])
        self.ultimo_assunto = f"contratar_{tipo}"
        return (f"💵 **Seguro {tipo.title()}**\n\n"
                f"💰 Preço: {info['preco']}\n"
                f"📝 Descrição: {info['descricao']}\n"
                f"🛡️ Coberturas:\n   ◦ {cov}\n\n"
                "✅ Deseja prosseguir com a contratação ou quer mais informações sobre as condições?")

    def _explicar_coberturas(self, mensagem: str) -> str:
        prompt = f"""
O usuário perguntou sobre coberturas: "{mensagem}"

Base de conhecimento (JSON):
{json.dumps(self.seguros_info, ensure_ascii=False)}

Explique de forma direta e clara quais coberturas existem e para quais situações cada seguro é mais adequado.
Responda em português brasileiro.
"""
        return self.gerar_resposta(prompt) or ("Posso explicar as coberturas principais: Vida (morte acidental, invalidez), "
                                               "Automóvel/Motocicleta (colisões, incêndio, roubo), Residencial (incêndio, roubos, danos elétricos).")

    def _resposta_padrao(self, mensagem: str) -> str:
        # Se o usuário respondeu "sim" e havia um assunto anterior, tratamos de forma simples:
        if mensagem.strip().lower() in {"sim", "claro", "pode", "ok", "quero"} and self.ultimo_assunto:
            assunto = self.ultimo_assunto
            self.ultimo_assunto = None
            if assunto.startswith("contratar_"):
                tipo = assunto.replace("contratar_", "")
                return f"Ótimo — vou abrir o processo de contratação do seguro {tipo.title()}. Alguém entrará em contato para confirmar dados. (Fluxo simulado)."
        # Caso geral: usar modelo para resposta curta com contexto
        contexto = json.dumps(self.seguros_info, ensure_ascii=False)
        system_prompt = f"""
Você é um assistente virtual especializado em seguros. A empresa oferece os seguintes produtos:
{contexto}

Seja útil, educado e direto. Se não souber algo, diga que pode encaminhar para um atendente.
Mantenha a resposta em português brasileiro.
"""
        resposta = self.gerar_resposta(mensagem, system_prompt)
        if not resposta:
            return "Desculpe, não entendi. Posso listar os seguros que oferecemos (Vida, Residencial, Automóvel/Motocicleta, Eletrodomésticos) ou informar preços. O que deseja?"
        return resposta

    # -------------------------
    # Fluxo principal
    # -------------------------
    def processar_mensagem(self, mensagem: str) -> str:
        # histórico simples
        self.historico.append({"role": "user", "text": mensagem})
        # classificação
        intent = self.classificar_intencao(mensagem)
        # log básico
        print(f"🎯 Intenção detectada: {intent}")

        if intent == "saudacao":
            resposta = self._responder_saudacao()
        elif intent == "despedida":
            resposta = self._responder_despedida()
        elif intent == "lista_seguros":
            resposta = self._listar_seguros()
        elif intent == "preco_seguro_vida":
            resposta = self._fornecer_preco("vida")
        elif intent == "preco_seguro_carro":
            resposta = self._fornecer_preco("automovel")
        elif intent == "preco_seguro_residencial":
            resposta = self._fornecer_preco("residencial")
        elif intent == "preco_seguro_eletrodomesticos":
            resposta = self._fornecer_preco("eletrodomesticos")
        elif intent == "preco_seguro_motocicleta":
            resposta = self._fornecer_preco("motocicleta")
        elif intent == "cobertura":
            resposta = self._explicar_coberturas(mensagem)
        else:
            resposta = self._resposta_padrao(mensagem)

        # salvar resposta no histórico
        self.historico.append({"role": "bot", "text": resposta})
        return resposta

    # modo interativo
    def chat_interativo(self):
        print("🔍 Verificando conexão com Ollama...")
        if not self.verificar_conexao_ollama():
            print("❌ Ollama não está rodando. Rode `ollama serve` para usar o modo IA.")
            print("Entrando em modo fallback local (respostas rápidas).")
            FallbackChat(self).chat()
            return

        print("✅ Ollama conectado. Iniciando chat (modo IA).")
        print("=" * 60)
        print(self._responder_saudacao())
        try:
            while True:
                mensagem = input("\n👤 Você: ").strip()
                if not mensagem:
                    continue
                if mensagem.lower() in {"sair", "exit", "quit", "tchau"}:
                    print("\n🤖 " + self._responder_despedida())
                    break
                print("🔄 Processando...")
                resposta = self.processar_mensagem(mensagem)
                print(f"\n🤖 Bot: {resposta}")
        except KeyboardInterrupt:
            print("\n\n🤖 " + self._responder_despedida())

class FallbackChat:
    """
    Modo rápido quando Ollama não está disponível.
    Usa respostas pré-definidas e heurísticas.
    """
    def __init__(self, bot: Optional[OllamaChatbotSeguros] = None):
        self.bot = bot or OllamaChatbotSeguros()
        self.fallback_responses = {
            "saudacao": "Olá! Sou assistente de seguros. Posso ajudar com preços e informações!",
            "lista_seguros": "Temos seguros: Vida, Automóvel (inclui motos), Residencial e Eletrodomésticos.",
            "preco_vida": "Seguro de Vida: R$ 89,90/mês.",
            "preco_automovel": "Seguro Automóvel: R$ 199,90/mês. Seguro Motocicleta: R$ 159,90/mês.",
            "preco_residencial": "Seguro Residencial: R$ 129,90/mês.",
            "preco_eletro": "Seguro Eletrodomésticos: R$ 39,90/mês.",
            "cobertura": "Cobrimos: vida (morte acidental, invalidez), automóvel/moto (colisões, incêndio, roubo) e residencial (incêndio, roubo, danos elétricos)."
        }

    def chat(self):
        print("🤖 Modo Fallback - Respostas rápidas")
        print("Digite 'sair' para encerrar.")
        try:
            while True:
                msg = input("\n👤 Você: ").strip().lower()
                if not msg:
                    continue
                if msg in {"sair", "exit", "quit", "tchau"}:
                    print("\n🤖 Obrigado! Até logo.")
                    break
                # heurísticas simples
                if any(g in msg for g in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]):
                    print("🤖 " + self.fallback_responses["saudacao"])
                elif any(p in msg for p in ["lista", "quais seguros", "tipos de seguros"]):
                    print("🤖 " + self.fallback_responses["lista_seguros"])
                elif any(p in msg for p in ["lavadora", "máquina de lavar", "eletro", "geladeira"]):
                    print("🤖 " + self.fallback_responses["preco_eletro"])
                elif any(p in msg for p in ["harley", "moto", "motocicleta"]):
                    print("🤖 " + self.fallback_responses["preco_automovel"])
                elif any(p in msg for p in ["vida", "morte", "invalidez"]):
                    print("🤖 " + self.fallback_responses["preco_vida"])
                elif any(p in msg for p in ["residencial", "casa", "apartamento"]):
                    print("🤖 " + self.fallback_responses["preco_residencial"])
                elif any(p in msg for p in ["acidentes", "cobre", "coberturas"]):
                    print("🤖 " + self.fallback_responses["cobertura"])
                elif any(p in msg for p in ["preço", "custa", "quanto"]):
                    print("🤖 " + self.fallback_responses["preco_automovel"])
                else:
                    # resposta genérica
                    print("🤖 Desculpe, não entendi completamente. Posso listar os seguros que oferecemos ou informar preços. O que deseja?")
        except KeyboardInterrupt:
            print("\n\n🤖 Obrigado! Até logo.")

if __name__ == "__main__":
    print("🚀 Iniciando Chatbot de Seguros...")
    bot = OllamaChatbotSeguros()
    bot.chat_interativo()
