# loot

Repositório central de ativos de automação e bibliotecas compartilhadas.

Consolida o conhecimento técnico da equipe em um único lugar, evitando retrabalho entre projetos.

## Propósito

Desafios técnicos de automação (Auth, ETL, Integrações) se repetem entre projetos. Este repositório centraliza essas soluções para:

1. Reduzir retrabalho reutilizando código já testado
2. Padronizar implementações recorrentes
3. Centralizar práticas de segurança (credenciais, retries, etc)

## Estrutura
O repositório organiza soluções agnósticas ao cliente/projeto:

* `/auth`: Módulos de autenticação (OAuth2 flows, gestão de tokens, cookies sessions).
* `/parsers`: Tratamento e normalização de dados (PDF, Excel, CSV, Strings regex).
* `/connectors`: Wrappers e clientes para APIs frequentes (Google Workspace, Slack, ERPs).
* `/helpers`: Utilitários de infraestrutura (Loggers, Decorators de retry, Tratamento de exceção).
* `/scaffolds`: Estruturas base para iniciar novos bots ou automações.

## Guia de Contribuição

Contribua com qualquer código reutilizável: funções genéricas, classes utilitárias ou scripts de configuração.

### Requisitos
1. **Sanitização:** Remova credenciais e dados sensíveis. Use variáveis de ambiente (`os.getenv`).
2. **Desacoplamento:** O código deve funcionar fora do contexto original.
3. **Documentação:** Adicione docstring explicando o que faz e suas dependências.
4. **Type Hints:** Adicione type hints em todas as funções.

### Type Hints

O pacote inclui suporte completo a type hints (`py.typed`). Ao adicionar código:

```python
from typing import TypedDict

# Com type hints
def validar_email(email: str) -> bool:
    """Valida formato de email."""
    return "@" in email

# Retorno complexo com TypedDict
class ResultadoValidacao(TypedDict):
    valido: bool
    mensagem: str

def processar_dados(valor: str) -> ResultadoValidacao:
    return {"valido": True, "mensagem": "OK"}

# Evitar: sem type hints
def validar_email(email):
    return "@" in email
```

O arquivo `py.typed` já está configurado. Basta adicionar type hints (`param: tipo` e `-> tipo_retorno`) em funções novas. Use TypedDict para dicts de retorno complexos.

## Instalação

### Via PyPI

```bash
# Com UV
uv add qegloot

# Com pip
pip install qegloot
```

### Via GitHub

```bash
uv pip install git+https://github.com/QualidadeGestaoBRMED/loot.git@v0.1.0
uv pip install git+https://github.com/QualidadeGestaoBRMED/loot.git
```

### Instalação local

```bash
git clone https://github.com/QualidadeGestaoBRMED/loot.git
cd loot
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## Uso

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