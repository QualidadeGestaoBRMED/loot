import json
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Optional, Dict, Any


_ALLOWED_STATUS = {"success", "failed", "warning"}


def normalize_status(status: str) -> str:
    s = (status or "").strip().lower()
    if s not in _ALLOWED_STATUS:
        return "failed"
    return s

def map_exit_code_to_status(rc: int) -> str:
    # 0 = success ; 1 = warning ; outros = failed
    if rc == 0:
        return "success"
    if rc == 1:
        return "warning"
    return "failed"


def default_summary(status: str) -> str:
    if status == "success":
        return "SUCCESS"
    if status == "warning":
        return "WARNING"
    return "FAILED"


@dataclass
class OrchestratorClientConfig:
    notify_url: str
    job_token: str
    timeout_seconds: int = 300
    max_log_chars: int = 2000


class _TeeStream:
    """Espelha saída para o stream original e captura até max_chars."""
    def __init__(self, original, max_chars: int):
        self.original = original
        self.max_chars = max_chars
        self._buf = []

    def write(self, s: str):
        try:
            self.original.write(s)
        except Exception:
            pass
        if s:
            current = "".join(self._buf)
            if len(current) < self.max_chars:
                remaining = self.max_chars - len(current)
                self._buf.append(s[:remaining])

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass

    @property
    def captured(self) -> str:
        return "".join(self._buf).strip()


class OrchestratorNotifier:
    """
    Notifica o orquestrador via HTTP usando curl (sem quebrar o job).

    Observação importante:
    - Isso NÃO captura SyntaxError do próprio arquivo (porque o Python nem executa).
      Para isso, use o CLI runner (brmed-orq-run) em runner.py.
    """

    def __init__(
        self,
        job_id: str,
        config: OrchestratorClientConfig,
        log_url: Optional[str] = None,
        capture_stdio: bool = False,
    ):
        self.job_id = job_id
        self.config = config
        self.log_url = log_url
        self.capture_stdio = capture_stdio

        self._t0: Optional[float] = None
        self._orig_stdout = None
        self._orig_stderr = None
        self._stdout_tee: Optional[_TeeStream] = None
        self._stderr_tee: Optional[_TeeStream] = None

    def start(self) -> None:
        self._t0 = time.monotonic()

    def __enter__(self):
        self.start()
        if self.capture_stdio:
            self._orig_stdout = sys.stdout
            self._orig_stderr = sys.stderr
            self._stdout_tee = _TeeStream(self._orig_stdout, self.config.max_log_chars)
            self._stderr_tee = _TeeStream(self._orig_stderr, self.config.max_log_chars)
            sys.stdout = self._stdout_tee  # type: ignore[assignment]
            sys.stderr = self._stderr_tee  # type: ignore[assignment]
        return self

    def __exit__(self, exc_type, exc, tb):
        self._restore_stdio()

        if exc is None:
            self.notify(status="success")
            return False

        # Runtime exception: manda failed + trace
        trace = "".join(traceback.format_exception(exc_type, exc, tb))
        summary = self._build_summary("failed", explicit_summary=None, extra_details=trace)

        # error_message deve ser curto (ex.: "Falhou ao processar ...")
        self.notify(
            status="failed",
            log_summary=summary,
            error_message=str(exc) if exc is not None else "Erro desconhecido",
        )
        return False  # mantém propagação da exceção

    def _restore_stdio(self) -> None:
        if self.capture_stdio and self._orig_stdout is not None and self._orig_stderr is not None:
            sys.stdout = self._orig_stdout  # type: ignore[assignment]
            sys.stderr = self._orig_stderr  # type: ignore[assignment]

    def _duration_seconds(self) -> Optional[int]:
        if self._t0 is None:
            return None
        return int(round(time.monotonic() - self._t0))

    def _build_summary(self, status: str, explicit_summary: Optional[str], extra_details: Optional[str]) -> str:
        base = (explicit_summary or "").strip() or default_summary(status)

        parts = []
        if self._stdout_tee and self._stdout_tee.captured:
            parts.append("STDOUT:\n" + self._stdout_tee.captured)
        if self._stderr_tee and self._stderr_tee.captured:
            parts.append("STDERR:\n" + self._stderr_tee.captured)
        if extra_details:
            parts.append("TRACE:\n" + extra_details)

        if not parts:
            return base

        full = base + "\n\n" + "\n\n".join(parts)
        return full[: self.config.max_log_chars]

    def notify(
        self,
        status: str,
        duration: Optional[int] = None,
        log_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Envia (schema):
        {
          "job_id": "...",
          "status": "success|warning|failed",
          "duration": 0,
          "log_summary": "... (tudo)",
          "error_message": "... (curto)",
          "log_url": "..."
        }

        Retorna True se curl saiu com code 0, senão False.
        Nunca levanta exceção.
        """
        try:
            st = normalize_status(status)

            dur = duration
            if dur is None:
                dur = self._duration_seconds()

            # log_summary aqui pode ser curto ou None; _build_summary sempre agrega stdout/stderr
            summary = self._build_summary(st, explicit_summary=log_summary, extra_details=None)

            payload: Dict[str, Any] = {"job_id": self.job_id, "status": st}
            if dur is not None:
                payload["duration"] = dur
            if summary:
                payload["log_summary"] = summary
            if error_message:
                payload["error_message"] = str(error_message)[: self.config.max_log_chars]
            if self.log_url is not None:
                payload["log_url"] = self.log_url

            if extra_fields:
                for k, v in extra_fields.items():
                    if k in ("job_id", "status"):
                        continue
                    payload[k] = v

            return self._curl_post(payload)
        except Exception:
            return False

    def notify_from_exit_code(
        self,
        rc: int,
        log_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self.notify(
            status=map_exit_code_to_status(rc),
            log_summary=log_summary,
            error_message=error_message,
            extra_fields=extra_fields,
        )

    def _curl_post(self, payload: Dict[str, Any]) -> bool:
        data = json.dumps(payload, ensure_ascii=False)

        cmd = [
            "curl",
            "-sS",
            "--fail-with-body", # testar caso dê algum problema no backend (ex.: 400) e ainda assim enviar o log_summary para diagnóstico
            "-X",
            "POST",
            self.config.notify_url,
            "-H",
            f"X-Token: {self.config.job_token}",
            "-H",
            "Content-Type: application/json",
            "-d",
            data,
        ]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.config.timeout_seconds,
                check=False,
            )
            return proc.returncode == 0
        except Exception:
            return False