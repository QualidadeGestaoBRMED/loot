import argparse
import os
import subprocess
import time
from typing import List, Optional

from .notifier import OrchestratorClientConfig, OrchestratorNotifier, map_exit_code_to_status


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="brmed-orq-run",
        description="Executa um comando/script e notifica o orquestrador (captura até SyntaxError).",
    )

    p.add_argument("--job-id", default=os.environ.get("JOB_ID"), help="Job ID (ou ENV JOB_ID)")
    p.add_argument("--notify-url", default=os.environ.get("NOTIFY_URL"), help="Notify URL (ou ENV NOTIFY_URL)")
    p.add_argument("--token", default=os.environ.get("JOB_TOKEN"), help="Token (ou ENV JOB_TOKEN)")
    p.add_argument("--log-url", default=os.environ.get("LOG_URL", ""), help="Log URL (ou ENV LOG_URL)")
    p.add_argument("--timeout", type=int, default=int(os.environ.get("ORQ_TIMEOUT", "15")))
    p.add_argument("--max-log-chars", type=int, default=int(os.environ.get("ORQ_MAX_LOG_CHARS", "2000")))
    p.add_argument("--status-on-rc1", default="warning", choices=["warning", "failed"], help="Como tratar RC=1")
    p.add_argument("--no-notify", action="store_true", help="Executa sem notificar (debug)")
    p.add_argument("--", dest="double_dash", action="store_true", help=argparse.SUPPRESS)

    # Tudo após o '--' (ou o restante) vira comando
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="Comando a executar. Ex: -- python main.py")

    args = p.parse_args(argv)

    # remove um leading '--' que o argparse mantém em REMAINDER
    if args.cmd and args.cmd[0] == "--":
        args.cmd = args.cmd[1:]

    return args


def _extract_error_message(stderr: str, stdout: str, max_len: int) -> str:
    """
    Retorna uma mensagem curta para o campo error_message.
    - Prioriza stderr
    - Se achar linha com 'SyntaxError', retorna ela
    - Senão retorna a última linha não-vazia
    """
    text = (stderr or stdout or "").strip()
    if not text:
        return ""

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ""

    # Preferir linha com SyntaxError / ModuleNotFoundError etc. (geralmente a última linha)
    for l in reversed(lines):
        if "SyntaxError" in l:
            return l[:max_len]

    # fallback: última linha costuma ser a mensagem do erro
    return lines[-1][:max_len]


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    if not args.cmd:
        raise SystemExit("Uso: brmed-orq-run --job-id <id> --notify-url <url> --token <token> -- <comando>")

    if not args.no_notify:
        if not args.job_id or not args.notify_url or not args.token:
            raise SystemExit("Faltam parâmetros: job-id/notify-url/token (ou defina ENV JOB_ID/NOTIFY_URL/JOB_TOKEN).")

        cfg = OrchestratorClientConfig(
            notify_url=args.notify_url,
            job_token=args.token,
            timeout_seconds=args.timeout,
            max_log_chars=args.max_log_chars,
        )
        notifier = OrchestratorNotifier(job_id=args.job_id, config=cfg, log_url=args.log_url, capture_stdio=False)
        notifier.start()
    else:
        notifier = None
        cfg = None  # type: ignore[assignment]

    t0 = time.monotonic()

    # Executa e captura saída: SyntaxError e import errors viram stderr + rc != 0
    proc = subprocess.run(args.cmd, capture_output=True, text=True)

    duration = int(round(time.monotonic() - t0))
    status = map_exit_code_to_status(proc.returncode)

    # opção: rc=1 pode ser tratado como failed dependendo do seu padrão
    if proc.returncode == 1 and args.status_on_rc1 == "failed":
        status = "failed"

    # log_summary = tudo (prioriza stderr)
    log_summary = (proc.stderr or proc.stdout or "").strip()
    if not log_summary:
        log_summary = f"--{status}--"

    # error_message = curto (só quando falhar)
    error_message = ""
    if status != "success":
        max_len = args.max_log_chars
        error_message = _extract_error_message(proc.stderr or "", proc.stdout or "", max_len)

    # truncagem e notify
    if notifier is not None:
        max_len = notifier.config.max_log_chars
        log_summary = log_summary[:max_len]
        if error_message:
            error_message = error_message[:max_len]

        notifier.notify(
            status=status,
            duration=duration,
            log_summary=log_summary,
            error_message=error_message or None,
        )

    raise SystemExit(proc.returncode)