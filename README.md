# Sports News Radar · Futebol e Andebol

Dashboard com 8 áreas: Manchester United, Primeira Liga, Superliga dinamarquesa, campeonato português de andebol, seleção portuguesa, campeonato dinamarquês, EHF e IHF.

**Tecnologia:** Google News RSS (17 pesquisas públicas), Python, GitHub Actions (hora a hora) e GitHub Pages. Retém 30 dias de metadados e apresenta estado de cada fonte. A tradução PT experimental usa MyMemory com limites; pode ser desativada removendo a função translate_budget de collector.py. Nunca acede ao texto integral de artigos.

**Publicar:** Settings > Pages > Deploy from a branch > main > /docs. O endereço será https://mageburx.github.io/sports-news-radar/ quando ativado. Em Actions > Sports News Radar > Run workflow é possível iniciar a primeira recolha. Se a escrita de dados falhar, verifica as permissões de escrita de GitHub Actions.

**Local:** python -m pip install -r requirements.txt; python -m unittest discover -s tests -v; python -m sports_radar.collector; python -m http.server 8000 (visitar /docs/).

É um agregador independente. Notícias podem não aparecer se não estiverem indexadas no Google News; não é uma API oficial de resultados e não apresenta jogos em direto. O agendamento GitHub Actions não garante execução ao minuto. O arquivo de 30 dias é aplicado ao JSON corrente, mas o histórico Git preserva versões anteriores.
