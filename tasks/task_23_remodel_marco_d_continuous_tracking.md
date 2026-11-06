# Task Specification: Remodelagem do Genshin Gem Wish — Marco D: Rastreamento Contínuo e Datasets Reais

## Contexto e Objetivo
Implementar o **Marco D** (o marco final do roadmap de remodelagem estabelecido em `ANTIGRAVITY_REMODELAR_OVERLAY_GENSHIN.md` e `docs/REMODEL_ROADMAP.md`):
1. **Importadores de Datasets com Verificação de Proveniência (`src/markers/importers.py`)**:
   - Conectar importadores modulares com checagem formal de proveniência (`DatasetProvenance`): origem, tipo de licença (CC-BY, MIT, etc.), atribuição obrigatória e checagem de integridade de esquema.
   - Suporte a formato padronizado GeoJSON e Community JSON.
2. **Rastreador Suavizado e Controle de Confiança (`src/tracking/smooth_tracker.py`)**:
   - Suavização contínua por Média Móvel Exponencial (EMA) sobre coordenadas $(x, y)$ e ângulo de bússola $\theta$ (usando média circular com $\sin \theta$ e $\cos \theta$ para tratar a descontinuidade $359^\circ \leftrightarrow 0^\circ$).
   - Controle estrito de confiança: se confiança $< 60\%$, o rastreador rejeita o frame e oculta marcadores para impedir alucinação de pontos.
3. **Gerenciador de Tiles de Referência Regional (`src/tracking/reference_tile_manager.py`)**:
   - Indexador de blocos e pirâmides de escala para correspondência de minimapa em tempo real nas regiões do jogo.
   - Integração com o dataset calibrado de Dragonspine e expansão para Liyue/Mondstadt.
4. **Integração no `src/app.py`**:
   - Integrar rastreador suavizado e importador de dados com proveniência.
5. **Testes Automatizados e Benchmarks**:
   - Criar `tests/test_continuous_tracking_and_importers.py`.
   - Executar `pytest tests/` garantindo 100% de aprovação (100+ testes).
   - Atualizar `scripts/run_benchmarks.py`, `docs/BENCHMARKS.md`, `docs/REMODEL_ROADMAP.md` e `README.md`.
6. **Recompilação do Executável Windows**:
   - Recompilar `GenshinOverlay.exe` usando o Python 3.12 do Windows.

---

## Workspace Root
Caminho absoluto: `/mnt/d/Projects/GenshinGemWish`
