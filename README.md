# loot
steal like an artist :)

**Repositório central de ativos de automação e bibliotecas compartilhadas.**

Este projeto materializa a filosofia *"Steal Like An Artist"*: nosso objetivo é consolidar o conhecimento técnico da equipe em um único lugar, evitando retrabalho e elevando a barra técnica dos nossos projetos individuais.

## 🎯 Propósito
Atualmente operamos em projetos distintos, mas os desafios técnicos de automação (Auth, ETL, Integrações) são recorrentes. O **Loot** serve para:

1.  **Aceleração:** Reduzir o *time-to-delivery* reutilizando módulos já testados.
2.  **Padronização:** Estabelecer padrões de código para problemas comuns antes da migração para Squads.
3.  **Segurança:** Centralizar implementações robustas (ex: tratamento correto de credenciais e retries).

## 📂 Estrutura
O repositório organiza soluções agnósticas ao cliente/projeto:

* `/auth`: Módulos de autenticação (OAuth2 flows, gestão de tokens, cookies sessions).
* `/parsers`: Tratamento e normalização de dados (PDF, Excel, CSV, Strings regex).
* `/connectors`: Wrappers e clientes para APIs frequentes (Google Workspace, Slack, ERPs).
* `/helpers`: Utilitários de infraestrutura (Loggers, Decorators de retry, Tratamento de exceção).
* `/scaffolds`: Estruturas base para iniciar novos bots ou automações.

## 🛠 Guia de Contribuição

A contribuição é encorajada para qualquer trecho de código que tenha valor reutilizável.

### O que trazer para cá?
* Funções genéricas que você escreveu para um projeto específico.
* Classes utilitárias que resolveram um problema complexo.
* Scripts de configuração que economizam tempo.

### Requisitos Básicos
1.  **Sanitização:** Remova **qualquer** credencial, chave de API ou dado sensível de cliente. Use variáveis de ambiente (`os.getenv`).
2.  **Desacoplamento:** O código deve funcionar fora do contexto do seu projeto original.
3.  **Documentação Mínima:** Adicione uma Docstring explicando:
    * O que o código faz.
    * Quais as dependências necessárias.

## 📦 Instalação

### Via PyPI (Recomendado)

```bash
# Com UV (recomendado)
uv add qegloot

# Com pip tradicional
pip install qegloot
```

### Via GitHub (Desenvolvimento)

```bash
# Versão específica
uv pip install git+https://github.com/QualidadeGestaoBRMED/loot.git@v0.1.0

# Última versão da main
uv pip install git+https://github.com/QualidadeGestaoBRMED/loot.git
```

### Instalação local (Contribuidores)

```bash
# Clone o repositório
git clone https://github.com/QualidadeGestaoBRMED/loot.git
cd loot

# Instale em modo editable com dependências de desenvolvimento
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## 🚀 Uso Rápido

```python
from loot.parsers import process_document, is_cpf_valid

# Processar e validar CPF
result = process_document("123.456.789-09")
print(result)
# {'original_input': '123.456.789-09', 'type': 'CPF',
#  'is_valid': True, 'clean_value': '12345678909',
#  'formatted': '123.456.789-09'}

# Validação direta
if is_cpf_valid("12345678909"):
    print("CPF válido!")
```