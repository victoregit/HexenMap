# Hexen Map Exporter (fonte)

Extensão Manifest V3 sem frameworks. O núcleo compartilhado fica em `data/import/appsample-core.js` para evitar cópias divergentes.

Gere a pasta completa e o ZIP a partir da raiz do repositório:

```powershell
python scripts/package_exporter.py
```

Carregue **dist/HexenMapExporter**, não esta pasta-fonte incompleta. Usuários recebem `dist/HexenMapExporter-0.2.0-teste.zip` pronto; não precisam de Python.

Consulte `docs/EXPORTER_INSTALL.html` e `docs/EXPORTER_TEST_REPORT.md`. Compatibilidade real ainda pendente de teste completo com conta conectada e desconectada no Chrome e Edge.

O envio opcional ao aplicativo usa nativeMessaging e exige ativação no Hexen Map atualizado. A chave pública no manifesto fixa a identidade entre instalações; não é uma credencial de conta nem uma assinatura de publicação.
