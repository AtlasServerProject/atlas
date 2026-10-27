# Verificação 0.4.0 — 27/10/2026

- TypeScript, build e formatação verificados.
- 45 testes automatizados passaram e cobrem manifesto assinado, integridade, retomada, cancelamento, rollback, caminhos, ZIP, autenticação simulada, cofre, concorrência e ambiente Java.
- As 56 fontes externas responderam à consulta. Um mod real foi baixado e conferido por SHA-256.
- Plano real Minecraft/Fabric resolvido: 3.951 arquivos, 63 entradas de classpath e oito bibliotecas nativas Windows.
- Java Windows e as oito bibliotecas nativas baixados e extraídos com verificações de integridade, CRC e caminhos. Nenhum binário Windows foi executado nesta VM.
- Renderer exercitado em navegador com ponte exclusiva de teste: catálogo real de 57 mods, busca, instalação/cancelamento, autorização simulada e bloqueio de Jogar sem conta.
- Backend não alterado; seus quatro testes HTTP pertencem à verificação anterior.

Pendentes: Client ID próprio do Atlas, autorização real Microsoft/Minecraft, DPAPI em Windows, instalação completa e execução do jogo em Windows. A janela Electron nativa não foi validada nesta VM por restrição do sandbox Linux; a proteção não foi desativada.

O ZIP é uma distribuição para teste, sem instalador ou assinatura Authenticode. Não houve implantação ou reinício dos serviços de produção. npm audit não substitui auditoria de segurança.

Pacote Windows 0.4.0 gerado: PE x64, ASAR, três vídeos locais e integridade ZIP conferidos; SHA-256 em arquivo separado.
