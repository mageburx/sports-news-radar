# Sports News Radar — Futebol e Andebol

Agregador independente e gratuito de **notícias públicas** para Manchester United, Primeira Liga de Portugal, Superliga dinamarquesa, campeonato português de andebol, seleção portuguesa de andebol, campeonato dinamarquês de andebol, EHF e IHF.

- Dashboard: `docs/index.html`, publicado por GitHub Pages a partir de `main /docs`.
- Fontes: `config/sources.json` (Google News RSS PT/EN/DA, incluindo pesquisas dirigidas a sites oficiais).
- Coletor: `sports_radar/collector.py` (títulos, excertos e ligações, nunca artigos completos).
- Atualização: GitHub Actions a cada hora; botão de execução manual em Actions.
- Arquivo: janela contínua de 30 dias em `docs/data/news.json`.
- Diagnóstico: `docs/data/status.json`, com número de notícias e erros por fonte.
- Sem custos de API obrigatórios. A cobertura depende da indexação Google News e do funcionamento dos feeds.

**Publicação:** Settings > Pages > Build and deployment > Deploy from a branch > main > /docs. URL esperado após ativar: https://mageburx.github.io/sports-news-radar/

**Primeira recolha:** Actions > Sports News Radar > Run workflow; o push inicial também deve iniciar uma execução. Se a gravação do JSON falhar por permissões, verifica Settings > Actions > General > Workflow permissions.

O cron GitHub Actions é de melhor esforço, pode atrasar. O arquivo não recupera notícias anteriores à primeira recolha; os commits Git continuam a guardar versões antigas. A designação “oficial” identifica publicações cujas ligações pertencem ao domínio da entidade oficial, não valida o conteúdo. Projeto independente, sem afiliação com federações, clubes ou ligas.
