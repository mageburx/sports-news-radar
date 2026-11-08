# Sports News Radar · Futebol e Andebol

Dashboard com 8 áreas: Manchester United, Primeira Liga, Superliga dinamarquesa, campeonato português de andebol, seleção portuguesa, campeonato dinamarquês, EHF e IHF.

**Tecnologia:** Google News RSS (20 pesquisas públicas), Python, GitHub Actions (hora a hora) e GitHub Pages. Retém 30 dias de metadados e apresenta estado de cada fonte. Os títulos provenientes de pesquisas dinamarquesas são traduzidos prioritariamente para inglês (DA→EN; títulos noruegueses podem usar NO→EN), com os excertos RSS traduzidos quando existe quota. As notícias de origem inglesa continuam a ter tradução experimental para PT; as portuguesas mantêm-se em PT. MyMemory é gratuito mas limitado e pode falhar; uma chave DeepL é opcional. O leitor pode alternar para «Ver original». O painel assinala a língua da tradução e não oculta a origem quando falha. Nunca acede ao texto integral de artigos.

**Publicar:** Settings > Pages > Deploy from a branch > main > /docs. O endereço será https://mageburx.github.io/sports-news-radar/ quando ativado. Em Actions > Sports News Radar > Run workflow é possível iniciar a primeira recolha. Se a escrita de dados falhar, verifica as permissões de escrita de GitHub Actions.

**Local:** python -m pip install -r requirements.txt; python -m unittest discover -s tests -v; python -m sports_radar.collector; python -m http.server 8000 (visitar /docs/).

É um agregador independente. Notícias podem não aparecer se não estiverem indexadas no Google News; não é uma API oficial de resultados e não apresenta jogos em direto. O agendamento GitHub Actions não garante execução ao minuto. O arquivo de 30 dias é aplicado ao JSON corrente, mas o histórico Git preserva versões anteriores.

**Tradução:** limite conservador de 4 200 caracteres/dia e até 8 artigos por execução (partilhado entre todas as traduções). As traduções pendentes são retomadas em execuções seguintes; erros têm nova tentativa após 12h. Configuração opcional: `DEEPL_API_KEY` (e `DEEPL_API_URL` para Pro) ou `MYMEMORY_EMAIL` como Secrets do GitHub Actions. Sem estes Secrets o bot tenta o MyMemory anónimo; o sucesso não é garantido.
