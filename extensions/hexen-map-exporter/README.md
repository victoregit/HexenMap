# Hexen Map Exporter (fonte)

Extensão Manifest V3 sem frameworks. O núcleo compartilhado fica em `data/import/appsample-core.js` para evitar cópias divergentes.

Gere a pasta completa e o ZIP a partir da raiz do repositório:

```powershell
python scripts/package_exporter.py
```

Carregue **dist/extensoes/2.0.4/HexenMapExporter**, não esta pasta-fonte incompleta. O pacote atual é `dist/extensoes/2.0.4/HexenMapExporter-2.0.4.zip`; usuários não precisam de Python. A versão exibida no popup é lida do manifesto da extensão carregada pelo navegador.

Consulte `docs/EXPORTER_INSTALL.html` e `docs/EXPORTER_TEST_REPORT.md`. Compatibilidade real ainda pendente de teste completo com conta conectada e desconectada no Chrome e Edge.

O envio opcional ao aplicativo usa nativeMessaging e exige ativação no Hexen Map atualizado. A chave pública no manifesto fixa a identidade entre instalações; não é uma credencial de conta nem uma assinatura de publicação.
