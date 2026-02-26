# brmed-orq

A seguir está uma documentação objetiva dos dois modos de uso da lib `brmed-orq`:

- Notificar pelo RC (wrapper externo / `start.sh`) - ideal para Docker Compose e para garantir notificação mesmo se o container falhar.
- Notificar dentro do código (`context manager` `with`) + Runner (`brmed-orq-run`) - ideal quando o usuário controla o script e/ou quer capturar até `SyntaxError` rodando via CLI.

## Instalação (dev)

```bash
pip install -U qegloot
```

## 1) Modo A - Notificar pelo RC (`start.sh` / wrapper externo)

### Quando usar

Use este modo quando:

- você executa o job via Docker Compose (ou qualquer comando externo),
- você já tem o exit code (RC) e quer apenas mapear para status,
- você quer notificar mesmo que o container finalize/caia (porque o wrapper externo continua existindo).

### `.env` esperado

Exemplo mínimo:

```env
JOB_TOKEN=xpto
NOTIFY_URL=https://orquestrador-backend.onrender.com/notify
JOB_ID=eb296571
LOG_URL=
BUILD=false
```

### `start.sh` (como você pediu)

Esse script roda `docker compose up`, captura o RC e notifica com a lib.

Não deixa a notificação quebrar o fluxo (equivalente ao `|| true` do `curl`).

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

set -a; [ -f .env ] && source .env; set +a

BUILD_FLAG=""
[ "${BUILD:-false}" = "true" ] && BUILD_FLAG="--build"

START_TS=$(date +%s)

set +e
docker compose up $BUILD_FLAG --abort-on-container-exit
RC=$?
set -e

DURATION=$(( $(date +%s) - START_TS ))

# Notifica via lib (não quebra)
python - <<PY >/dev/null 2>&1 || true
from brmed_orq import OrchestratorClientConfig, OrchestratorNotifier, map_exit_code_to_status
cfg = OrchestratorClientConfig(notify_url="${NOTIFY_URL}", job_token="${JOB_TOKEN}")
OrchestratorNotifier(job_id="${JOB_ID}", config=cfg, log_url="${LOG_URL:-}").notify(
    status=map_exit_code_to_status(${RC}),
    duration=${DURATION},
)
PY

docker compose down --remove-orphans
exit "$RC"
```

### Como rodar
```bash
./start.sh
```

### Caso .SH ainda não seja um executável use com o comando:
```bash
chmod +x start.sh
```
Depois:
```bash
./start.sh
```

### Observações

- Esse modo não depende de alterar `main.py`.
- O status segue o mapeamento da lib: `0=success`, `1=warning`, outros=`failed`.

## 2) Modo B - Notificar dentro do código (`with`) e/ou usar Runner (`brmed-orq-run`)

Este modo tem duas partes que podem ser usadas separadas ou combinadas.

### 2.1) Notificar dentro do código com `with OrchestratorNotifier(...)`

#### Quando usar

Use quando:

- você quer capturar exceptions em runtime (durante a execução),
- quer capturar `stdout/stderr` (ex.: `print`, `traceback`) no `log_summary`.

Importante: não captura `SyntaxError` no próprio arquivo, porque o Python não chega a executar o script.

#### Exemplo `main.py`

```env
JOB_TOKEN=xpto
NOTIFY_URL=https://orquestrador-backend.onrender.com/notify
JOB_ID=eb296571
LOG_URL=
BUILD=false
```

```python
from brmed_orq import OrchestratorClientConfig, OrchestratorNotifier

def main():

    cfg = OrchestratorClientConfig(notify_url=NOTIFY_URL, job_token=JOB_TOKEN)

    with OrchestratorNotifier(job_id=JOB_ID, config=cfg, log_url=LOG_URL, capture_stdio=True):
        print("olá")
        # seu código aqui...
        # raise RuntimeError("falha em runtime")  # exemplo

if __name__ == "__main__":
    main()
```

#### Como rodar

```bash
python main.py
```

### 2.2) Runner no terminal: `brmed-orq-run -- python main.py`

#### Quando usar

Use quando:

- você quer capturar qualquer falha, inclusive:
- `SyntaxError`
- erro de import
- arquivo nem "compila"
- você não quer (ou não pode) alterar o `main.py`.

#### Requisitos

Você precisa fornecer variáveis por `.env` ou `export` no shell:

- `JOB_ID`
- `NOTIFY_URL`
- `JOB_TOKEN`
- `LOG_URL` (opcional)

#### Execução direta com flags

```bash
brmed-orq-run --job-id eb296571 --notify-url "https://.../notify" --token "xpto" -- python main.py
```

#### Exemplo com `.env`

```env
JOB_TOKEN=xpto
NOTIFY_URL=https://orquestrador-backend.onrender.com/notify
JOB_ID=eb296571
LOG_URL=
```

#### Rodando via terminal (carregando `.env`)

```bash
set -a; source .env; set +a
brmed-orq-run -- python main.py
```

#### Colocando em um `.sh` (ex.: `run_main.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

set -a; source .env; set +a
brmed-orq-run -- python main.py
```

## Mapeamento de status

- `rc=0` => `success`
- `rc=1` => `warning` (padrão; pode virar `failed` com `--status-on-rc1 failed`)
- `rc>1` => `failed`

## Como você usa no seu caso (com `SyntaxError`)

Em vez de:

```bash
python main.py
```

Use:

```bash
export JOB_TOKEN="xpto"
export NOTIFY_URL="https://orquestrador-backend.onrender.com/notify"
export JOB_ID="eb296571"
brmed-orq-run -- python main.py
```