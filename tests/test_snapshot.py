import hashlib
from urllib.error import HTTPError, URLError

import pytest

from pipeline import snapshot

_URL = "https://example.invalid/snapshot.duckdb?token=secret-test-token"


class _Response:
    def __init__(self, conteudo: bytes, *, status: int = 200, falhar_apos=None):
        self._conteudo = conteudo
        self._status = status
        self._falhar_apos = falhar_apos
        self._offset = 0
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def getcode(self):
        return self._status

    def read(self, tamanho):
        if self._falhar_apos is not None and self._offset >= self._falhar_apos:
            raise OSError("conexão interrompida")
        limite = tamanho
        if self._falhar_apos is not None:
            limite = min(limite, self._falhar_apos - self._offset)
        bloco = self._conteudo[self._offset : self._offset + limite]
        self._offset += len(bloco)
        return bloco


def _configurar(monkeypatch, conteudo: bytes):
    monkeypatch.setenv("MOVIE_DATA_SNAPSHOT_URL", _URL)
    monkeypatch.setenv(
        "MOVIE_DATA_SNAPSHOT_SHA256", hashlib.sha256(conteudo).hexdigest()
    )


def _arquivos_parciais(diretorio):
    return list(diretorio.glob("*.part")) + list(diretorio.glob(".*.part"))


def test_ausencia_de_configuracao_nao_tenta_baixar(tmp_path, monkeypatch):
    monkeypatch.delenv("MOVIE_DATA_SNAPSHOT_URL", raising=False)
    monkeypatch.delenv("MOVIE_DATA_SNAPSHOT_SHA256", raising=False)

    def falha_se_chamado(*_, **__):
        pytest.fail("urlopen não deveria ser chamado sem configuração")

    monkeypatch.setattr(snapshot, "urlopen", falha_se_chamado)

    assert snapshot.snapshot_configurado() is False
    assert snapshot.provisionar_snapshot(tmp_path / "snapshot.duckdb") is None
    assert list(tmp_path.iterdir()) == []


def test_configuracao_parcial_falha_sem_tentar_rede(monkeypatch):
    monkeypatch.setenv("MOVIE_DATA_SNAPSHOT_URL", _URL)
    monkeypatch.delenv("MOVIE_DATA_SNAPSHOT_SHA256", raising=False)
    monkeypatch.setattr(
        snapshot,
        "urlopen",
        lambda *_, **__: pytest.fail("urlopen não deveria ser chamado"),
    )

    with pytest.raises(snapshot.SnapshotError, match="Configure"):
        snapshot.provisionar_snapshot()


def test_download_valido_instala_arquivo_com_checksum_correto(tmp_path, monkeypatch):
    conteudo = b"duckdb snapshot experimental"
    _configurar(monkeypatch, conteudo)
    chamadas = []

    def fake_urlopen(requisicao, *, timeout):
        chamadas.append((requisicao.full_url, timeout))
        return _Response(conteudo)

    monkeypatch.setattr(snapshot, "urlopen", fake_urlopen)
    destino = tmp_path / "snapshot.duckdb"

    resultado = snapshot.provisionar_snapshot(destino)

    assert resultado == destino
    assert destino.read_bytes() == conteudo
    assert (
        hashlib.sha256(destino.read_bytes()).hexdigest()
        == hashlib.sha256(conteudo).hexdigest()
    )
    assert chamadas == [(_URL, snapshot._TIMEOUT_SEGUNDOS)]
    assert _arquivos_parciais(tmp_path) == []


def test_destino_padrao_do_snapshot_fica_no_diretorio_temporario(tmp_path, monkeypatch):
    conteudo = b"snapshot no diretorio temporario"
    _configurar(monkeypatch, conteudo)
    monkeypatch.setattr(snapshot.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(snapshot, "urlopen", lambda *_, **__: _Response(conteudo))

    resultado = snapshot.provisionar_snapshot()

    assert resultado == tmp_path / "movie_data_snapshot.duckdb"
    assert resultado.read_bytes() == conteudo


def test_checksum_incorreto_rejeita_download_e_remove_parcial(tmp_path, monkeypatch):
    conteudo = b"snapshot com conteudo diferente do hash configurado"
    _configurar(monkeypatch, b"outro conteudo")
    monkeypatch.setattr(snapshot, "urlopen", lambda *_, **__: _Response(conteudo))
    destino = tmp_path / "snapshot.duckdb"

    with pytest.raises(snapshot.SnapshotError, match="SHA-256") as erro:
        snapshot.provisionar_snapshot(destino)

    assert "secret-test-token" not in str(erro.value)
    assert not destino.exists()
    assert _arquivos_parciais(tmp_path) == []


def test_falha_de_conexao_apresenta_erro_sem_expor_url(tmp_path, monkeypatch):
    conteudo = b"arquivo esperado"
    _configurar(monkeypatch, conteudo)

    def falha_de_conexao(*_, **__):
        raise URLError("servidor inacessivel")

    monkeypatch.setattr(snapshot, "urlopen", falha_de_conexao)
    destino = tmp_path / "snapshot.duckdb"

    with pytest.raises(snapshot.SnapshotError, match="URLError") as erro:
        snapshot.provisionar_snapshot(destino)

    assert "secret-test-token" not in str(erro.value)
    assert not destino.exists()
    assert _arquivos_parciais(tmp_path) == []


def test_resposta_http_com_erro_e_rejeitada(tmp_path, monkeypatch):
    conteudo = b"snapshot"
    _configurar(monkeypatch, conteudo)
    monkeypatch.setattr(
        snapshot,
        "urlopen",
        lambda *_, **__: _Response(conteudo, status=404),
    )
    destino = tmp_path / "snapshot.duckdb"

    with pytest.raises(snapshot.SnapshotError, match="HTTP 404"):
        snapshot.provisionar_snapshot(destino)

    assert not destino.exists()
    assert _arquivos_parciais(tmp_path) == []


def test_download_interrompido_remove_arquivo_parcial(tmp_path, monkeypatch):
    conteudo = b"conteudo parcial que nao deve ser aceito"
    _configurar(monkeypatch, conteudo)
    monkeypatch.setattr(
        snapshot,
        "urlopen",
        lambda *_, **__: _Response(conteudo, falhar_apos=7),
    )
    destino = tmp_path / "snapshot.duckdb"

    with pytest.raises(snapshot.SnapshotError, match="OSError"):
        snapshot.provisionar_snapshot(destino)

    assert not destino.exists()
    assert _arquivos_parciais(tmp_path) == []


def test_arquivo_existente_invalido_e_substituido_apos_validacao(tmp_path, monkeypatch):
    conteudo = b"snapshot correto"
    _configurar(monkeypatch, conteudo)
    destino = tmp_path / "snapshot.duckdb"
    destino.write_bytes(b"arquivo incompleto")
    chamadas = []

    def fake_urlopen(*_, **__):
        chamadas.append(True)
        return _Response(conteudo)

    monkeypatch.setattr(snapshot, "urlopen", fake_urlopen)

    resultado = snapshot.provisionar_snapshot(destino)

    assert resultado == destino
    assert destino.read_bytes() == conteudo
    assert chamadas == [True]
    assert _arquivos_parciais(tmp_path) == []


def test_arquivo_existente_com_hash_valido_e_reutilizado(tmp_path, monkeypatch):
    conteudo = b"snapshot previamente validado"
    _configurar(monkeypatch, conteudo)
    destino = tmp_path / "snapshot.duckdb"
    destino.write_bytes(conteudo)
    monkeypatch.setattr(
        snapshot,
        "urlopen",
        lambda *_, **__: pytest.fail("arquivo validado deveria ser reutilizado"),
    )

    assert snapshot.provisionar_snapshot(destino) == destino
    assert destino.read_bytes() == conteudo


def test_checksum_malformado_e_rejeitado_antes_do_download(monkeypatch):
    monkeypatch.setenv("MOVIE_DATA_SNAPSHOT_URL", _URL)
    monkeypatch.setenv("MOVIE_DATA_SNAPSHOT_SHA256", "abc123")
    monkeypatch.setattr(
        snapshot,
        "urlopen",
        lambda *_, **__: pytest.fail("checksum inválido não deve iniciar download"),
    )

    with pytest.raises(snapshot.SnapshotError, match="64 caracteres"):
        snapshot.snapshot_configurado()


def test_url_sem_https_e_rejeitada_antes_do_download(monkeypatch):
    monkeypatch.setenv("MOVIE_DATA_SNAPSHOT_URL", "http://example.invalid/snapshot")
    monkeypatch.setenv("MOVIE_DATA_SNAPSHOT_SHA256", "a" * 64)
    monkeypatch.setattr(
        snapshot,
        "urlopen",
        lambda *_, **__: pytest.fail("URL insegura não deve iniciar download"),
    )

    with pytest.raises(snapshot.SnapshotError, match="URL HTTPS"):
        snapshot.snapshot_configurado()


def test_http_error_real_exibe_status_sem_expor_url(tmp_path, monkeypatch):
    conteudo = b"snapshot esperado"
    _configurar(monkeypatch, conteudo)

    def resposta_http(*_, **__):
        raise HTTPError(_URL, 404, "Not Found", {}, None)

    monkeypatch.setattr(snapshot, "urlopen", resposta_http)
    destino = tmp_path / "snapshot.duckdb"

    with pytest.raises(snapshot.SnapshotError, match="HTTP 404") as erro:
        snapshot.provisionar_snapshot(destino)

    assert "secret-test-token" not in str(erro.value)
    assert not destino.exists()
    assert _arquivos_parciais(tmp_path) == []
