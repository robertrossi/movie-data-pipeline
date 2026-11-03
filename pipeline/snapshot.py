"""Provisiona o snapshot DuckDB remoto com validação de integridade."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_VAR_URL = "MOVIE_DATA_SNAPSHOT_URL"
_VAR_SHA256 = "MOVIE_DATA_SNAPSHOT_SHA256"
_TIMEOUT_SEGUNDOS = 30
_TAMANHO_CHUNK = 1024 * 1024


class SnapshotError(RuntimeError):
    """Erro compreensível de configuração, download ou integridade."""


def snapshot_configurado() -> bool:
    """Valida a configuração remota e informa se o modo snapshot está ativo.

    Se ambas as variáveis estiverem ausentes ou vazias, não há download.
    Configuração parcial ou URL/checksum inválido falha antes de qualquer rede.
    """
    url = os.environ.get(_VAR_URL, "").strip()
    checksum = os.environ.get(_VAR_SHA256, "").strip()
    if not url and not checksum:
        return False
    if not url or not checksum:
        raise SnapshotError(
            f"Configure {_VAR_URL} e {_VAR_SHA256} juntos para usar o snapshot."
        )

    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise SnapshotError(f"{_VAR_URL} deve ser uma URL HTTPS válida.")
    if re.fullmatch(r"[0-9a-fA-F]{64}", checksum) is None:
        raise SnapshotError(f"{_VAR_SHA256} deve conter 64 caracteres hexadecimais.")
    return True


def _configuracao() -> tuple[str, str] | None:
    if not snapshot_configurado():
        return None
    return (
        os.environ[_VAR_URL].strip(),
        os.environ[_VAR_SHA256].strip().lower(),
    )


def _sha256_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(_TAMANHO_CHUNK), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _destino_padrao() -> Path:
    """Usa o diretório temporário do sistema, também disponível no Cloud."""
    return Path(tempfile.gettempdir()) / "movie_data_snapshot.duckdb"


def provisionar_snapshot(destino: Path | str | None = None) -> Path | None:
    """Baixa, valida e instala atomicamente o snapshot configurado.

    Com as variáveis de snapshot ausentes, retorna ``None`` sem iniciar uma
    conexão de rede. Um arquivo já validado pelo SHA-256 é reutilizado.
    """
    configuracao = _configuracao()
    if configuracao is None:
        return None
    url, checksum_esperado = configuracao
    caminho_destino = Path(destino) if destino is not None else _destino_padrao()

    if caminho_destino.is_file():
        try:
            if hmac.compare_digest(_sha256_arquivo(caminho_destino), checksum_esperado):
                return caminho_destino
        except OSError:
            # Trate um arquivo ilegível como inválido e tente substituí-lo.
            pass

    try:
        caminho_destino.parent.mkdir(parents=True, exist_ok=True)
        caminho_temporario: Path | None = None
        digest = hashlib.sha256()
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{caminho_destino.name}.",
                suffix=".part",
                dir=caminho_destino.parent,
                delete=False,
            ) as arquivo_temporario:
                caminho_temporario = Path(arquivo_temporario.name)
                requisicao = Request(url, headers={"User-Agent": "MovieAnalytics/1.0"})
                with urlopen(requisicao, timeout=_TIMEOUT_SEGUNDOS) as resposta:
                    status = getattr(resposta, "status", None)
                    if status is None:
                        status = resposta.getcode()
                    if status != 200:
                        raise SnapshotError(
                            f"O servidor do snapshot respondeu com HTTP {status}."
                        )
                    while bloco := resposta.read(_TAMANHO_CHUNK):
                        arquivo_temporario.write(bloco)
                        digest.update(bloco)
                arquivo_temporario.flush()
                os.fsync(arquivo_temporario.fileno())

            checksum_calculado = digest.hexdigest()
            if not hmac.compare_digest(checksum_calculado, checksum_esperado):
                raise SnapshotError(
                    "O SHA-256 do snapshot baixado não corresponde ao valor configurado."
                )
            os.replace(caminho_temporario, caminho_destino)
            caminho_temporario = None
            return caminho_destino
        finally:
            if caminho_temporario is not None:
                caminho_temporario.unlink(missing_ok=True)
    except SnapshotError:
        raise
    except HTTPError as erro:
        raise SnapshotError(
            f"O servidor do snapshot respondeu com HTTP {erro.code}."
        ) from None
    except (URLError, TimeoutError, OSError, ValueError) as erro:
        # Não propaga a exceção original: sua mensagem pode conter a URL/token.
        raise SnapshotError(
            f"Falha ao baixar ou instalar o snapshot ({type(erro).__name__})."
        ) from None
