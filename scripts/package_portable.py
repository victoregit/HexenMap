"""Build a clean private-test portable package from explicitly listed runtime files."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.identity import VERSION


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def referenced(data):
    if isinstance(data,dict):
        if isinstance(data.get('file'),str) and isinstance(data.get('sha256'),str):yield data
        for value in data.values():yield from referenced(value)
    elif isinstance(data,list):
        for value in data:yield from referenced(value)


def main():
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%SZ')
    base=ROOT/'dist/atual'/f'HexenMap-{VERSION}'
    archive=base.parent/f'HexenMap-{VERSION}-Windows-x64.zip'
    if (base/'package-report.json').exists() or archive.exists():
        raise FileExistsError('Essa versão já foi empacotada. Incremente a versão ou arquive a pasta e o ZIP anteriores antes de gerar novamente.')
    base.mkdir(parents=True,exist_ok=True)
    package=base/'Hexen Map';package.mkdir()
    def copy(source,relative):
        target=package/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    def manifest(source,relative):
        data=json.loads(source.read_text(encoding='utf-8'))
        copy(source,relative)
        for entry in referenced(data):
            path=(source.parent/entry['file']).resolve()
            if not path.is_relative_to(source.parent.resolve()):raise ValueError('Reference outside package')
            if digest(path)!=entry['sha256']:raise ValueError(f'Hash mismatch: {path}')
            copy(path,relative.parent/entry['file'])
    copy(ROOT/'build/release-staging/HexenMap.exe',Path('HexenMap.exe'))
    copy(ROOT/'build/release-staging/HexenMapBridge.exe',Path('HexenMapBridge.exe'))
    manifest(ROOT/'userData/catalogs/appsample/SOURCE.json',Path('userData/catalogs/appsample/SOURCE.json'))
    for path in (ROOT/'userData/references/appsample').rglob('manifest.json'):
        manifest(path,path.relative_to(ROOT))
    manifest(ROOT/'userData/assets/appsample/SOURCE.json',Path('userData/assets/appsample/SOURCE.json'))
    # Only existing map tiles from the qualified personal dataset, never logs or saves.
    for level in ('12','14'):
        for path in (ROOT/'userData/reference-tile-cache/appsample-teyvat-v72'/level).glob('*.jpg'):
            copy(path,path.relative_to(ROOT))
    for kind in ('chests','oculi'):
        data=json.loads((ROOT/f'data/assets/{kind}/SOURCE.json').read_text(encoding='utf-8'))
        for entry in data['icons'].values():
            path=ROOT/f'userData/assets/{kind}'/entry['file']
            if digest(path)!=entry['sha256']:raise ValueError(f'Invalid artwork: {path}')
            copy(path,Path(f'userData/assets/{kind}')/entry['file'])
        copy(ROOT/f'data/assets/{kind}/SOURCE.json',Path(f'creditos/{kind}-SOURCE.json'))
    # Only cropped detector templates; never recordings/calibration frames.
    manifest(ROOT/'userData/automark/manifest.json',Path('userData/automark/manifest.json'))
    settings={'package':'appsample','categories':[],'performance_mode':'light','automark':False,
        'capture_visible':False,'server':'America','regional':{'appsample':{'categories':[],
        'area':None,'layer':'as-map-2 / surface'}},'panel':{'collapsed':False,'detached':True}}
    (package/'userData/settings.json').write_text(json.dumps(settings,indent=2),encoding='utf-8')
    readme=f'HEXEN MAP {VERSION} — BUILD PRIVADA DE TESTE\n'+'''

Windows 10/11 de 64 bits. Não precisa instalar Python, Git ou ferramentas de programação.

1. Extraia TODO o ZIP para uma pasta sua (por exemplo Documentos\\Hexen Map).
2. Abra HexenMap.exe. Não execute de dentro do ZIP e mantenha a pasta userData junto dele.
3. Abra o Genshin em janela ou sem bordas e escolha os itens desejados no painel.
   Os grupos começam recolhidos. Nenhum item selecionado = nenhum ícone.
4. Ao abrir, o Windows solicitará permissão de administrador, necessária para interagir com o jogo elevado.

F8: abrir/recolher painel. Ctrl+clique: marcar/desmarcar um item.
F9: coletar próximo. F10: desfazer. Atalhos configuráveis em Ajustes.
Não há bússola ou busca guiada. AutoMark é beta, desligado por padrão e qualificado em HUD PT-BR.
Modo Leve padrão. Modo Global opcional consome mais memória.
Progresso é salvo nesta pasta. Não apague userData ao atualizar; faça backup.

Esta cópia começa sem coletas, sem conta e sem preferências pessoais do autor.
Não exige login no AppSample para usar o catálogo incluído. Importar progresso é opcional,
em Ajustes, com confirmação e backup. O guia experimental de exportação também está ali.

Cobertura: catálogo importado AppSample e referências instaladas da superfície de Teyvat.
Cavernas/mapas separados sem referências permanecem indisponíveis. Os dados não equivalem
a validação em jogo de todos os pontos. A localização pode precisar se recuperar após viagens.
Use Encerrar overlay para sair. O aplicativo não executa comandos nem lê a memória do jogo.

Teste privado solicitado pelo responsável, não um instalador público. As condições de origem
dos arquivos acompanham seus manifestos; não foi estabelecida licença geral de redistribuição
de mapas/arte. Créditos: AppSample (marcadores/mapas), HoYoverse (arte do jogo).
Nomes localizados: AppSample, HoYoWiki e theBowja/genshin-db (MIT, licença anexa).

Se houver falha, informe mapa/camada, resolução, modo janela/sem bordas e o erro exibido.
Não envie cookies, tokens, HAR ou dados de login.
'''
    (package/'LEIA-ME.txt').write_text(readme,encoding='utf-8-sig')
    for name in ('NOTICE.md','THIRD_PARTY_LICENSES.txt'):
        copy(ROOT/'data/localization'/name,Path('creditos')/name)
    if (ROOT/'docs/STABILITY.md').exists():copy(ROOT/'docs/STABILITY.md',Path('ESTABILIDADE.md'))
    if (ROOT/'docs/HOTFIX_CTRL_AUTOMARK.md').exists():copy(ROOT/'docs/HOTFIX_CTRL_AUTOMARK.md',Path('HOTFIX_CTRL_AUTOMARK.md'))
    if (ROOT/'docs/EXPLORATION_UI.md').exists():copy(ROOT/'docs/EXPLORATION_UI.md',Path('PAINEL_E_MAPA.md'))
    report={'build':stamp,'version':VERSION,'private_test':True,'personal_progress_included':False,
        'python_required':False,'coverage':'as-map-2 / surface',
        'files':{str(p.relative_to(package)).replace('\\','/'):digest(p) for p in sorted(package.rglob('*')) if p.is_file()}}
    (package/'BUILD.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=base.parent/f'HexenMap-{VERSION}-Windows-x64.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for path in sorted(package.rglob('*')):
            if path.is_file():output.write(path,Path('Hexen Map')/path.relative_to(package))
    result={'zip':str(archive),'directory':str(package),'sha256':digest(archive),
        'size_mib':round(archive.stat().st_size/1024**2,1),'files':len(report['files'])+1}
    (base/'package-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
