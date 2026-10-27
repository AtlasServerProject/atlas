# Conferência corrigida do addon de lendários

O Mega Showdown 1.3.1 está no modpack e no servidor com o mesmo SHA-256. A contagem anterior de 34 estava incompleta: faltavam as alterações de `species_additions`, que usam `target` para habilitar espécies, além dos posers implementados em classes Java/Kotlin.

A conferência corrigida encontrou **86/94 espécies** com dados e recursos normal/shiny presentes. Veja o [catálogo atualizado](generations.catalogue.md). O JSON registra evidências por prêmio, incluindo arquivo, caminho do resolver, modelo, poser e textura.

As oito pendentes ainda exigem investigação: Celebi, Jirachi, Cresselia, Manaphy, Phione, Magearna, Zeraora e Pecharunt. As sprites delas no pacote de texturas não foram tratadas como prova de modelo 3D. Não houve teste individual em jogo nem ativação de prêmios.

Reproduzir: executar `build-catalogue.py --mods <pasta> --output generations.catalogue.json`, depois `verify-installed-assets.py --mods <pasta> --catalogue generations.catalogue.json`.
