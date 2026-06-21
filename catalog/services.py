'''Download remoto do acervo PROF-TONI a partir do GitHub.

Baixa o tarball do repositório configurado (privado) via API do GitHub,
extrai num diretório temporário e devolve o caminho da raiz extraída —
pronto para ser consumido pelo management command ``import_acervo``.
'''

import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings


class AcervoDownloadError(Exception):
    '''Falha ao baixar/extrair o acervo do GitHub.'''


def _tarball_url():
    repo = settings.ACERVO_GITHUB_REPO
    ref = settings.ACERVO_GITHUB_REF
    return 'https://api.github.com/repos/{0}/tarball/{1}'.format(repo, ref)


def download_acervo(dest_dir):
    '''Baixa e extrai o acervo em ``dest_dir``; devolve a raiz extraída.

    ``dest_dir`` deve ser um diretório já existente (idealmente um
    ``TemporaryDirectory``). Levanta ``AcervoDownloadError`` com mensagem
    amigável em qualquer falha (token ausente, 401/404, rede, tar inválido).
    '''
    token = settings.ACERVO_GITHUB_TOKEN
    if not token:
        raise AcervoDownloadError(
            'Token do GitHub não configurado (ACERVO_GITHUB_TOKEN).'
        )

    request = urllib.request.Request(
        _tarball_url(),
        headers={
            'Authorization': 'Bearer {0}'.format(token),
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'professordash-acervo-import',
            'X-GitHub-Api-Version': '2022-11-28',
        },
    )

    dest_path = Path(dest_dir)
    tar_path = dest_path / 'acervo.tar.gz'

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            tar_path.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise AcervoDownloadError(
                'GitHub recusou o acesso (HTTP {0}). Verifique o token e suas '
                'permissões de leitura no repositório.'.format(exc.code)
            ) from exc
        if exc.code == 404:
            raise AcervoDownloadError(
                'Repositório ou referência não encontrados '
                '({0}@{1}).'.format(
                    settings.ACERVO_GITHUB_REPO, settings.ACERVO_GITHUB_REF
                )
            ) from exc
        raise AcervoDownloadError(
            'Erro HTTP {0} ao baixar o acervo.'.format(exc.code)
        ) from exc
    except urllib.error.URLError as exc:
        raise AcervoDownloadError(
            'Falha de rede ao acessar o GitHub: {0}'.format(exc.reason)
        ) from exc

    extract_root = dest_path / 'extract'
    extract_root.mkdir(exist_ok=True)

    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(extract_root, filter='data')
    except (tarfile.TarError, OSError) as exc:
        raise AcervoDownloadError(
            'Arquivo do GitHub inválido ou corrompido: {0}'.format(exc)
        ) from exc

    # O GitHub empacota tudo sob um único diretório raiz (repo-sha/...).
    children = [child for child in extract_root.iterdir() if child.is_dir()]
    if len(children) != 1:
        raise AcervoDownloadError(
            'Estrutura inesperada no tarball do GitHub.'
        )

    root = children[0]
    if not (root / 'manifesto.json').exists():
        raise AcervoDownloadError(
            'manifesto.json não encontrado na raiz do acervo baixado.'
        )

    return root
