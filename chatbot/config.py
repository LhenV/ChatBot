# config.py
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "model": "llama3.2",
    "timeout": 60,
    "temperature": 0.3,
    "max_tokens": 500
}

SEGUROS_CONFIG = {
    "vida": {"preco": "R$ 89,90/mês", "destaque": "Proteção familiar"},
    "carro": {"preco": "R$ 199,90/mês", "destaque": "Cobertura completa"},
    "residencial": {"preco": "R$ 129,90/mês", "destaque": "Proteção patrimonial"},
    "motocicleta": {"preco": "R$ 159,90/mês", "destaque": "Especial para motos"},
    "eletrodomesticos": {"preco": "R$ 39,90/mês", "destaque": "Eletrodomésticos"}
}