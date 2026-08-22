# Angola Oportunidades V3 — Pacote de Categorias

Pacote preparado para integrar no projeto Angola Oportunidades V3.

## Conteúdo

- `data/categories.json` — categorias principais e subcategorias.
- `data/event-space-filters.json` — filtros específicos para **Aluguer de espaços para festas e eventos**.
- `data/ad-fields.json` — campos gerais para publicação de anúncios.
- `data/provinces.json` — lista de províncias de Angola.

## Categoria principal adicionada/corrigida

`Aluguer de espaços para festas e eventos`

Subcategorias:
- Salões de festas
- Espaços para casamentos
- Espaços para aniversários
- Quintais para eventos
- Espaços para confraternizações
- Espaços para reuniões
- Espaços para batizados
- Espaços com piscina
- Outros espaços para eventos

## Integração

Este pacote é um conjunto de dados/configuração e não substitui automaticamente os ficheiros existentes do projeto.
Antes de substituir categorias no projeto, faça uma cópia de segurança.

Para integrar, importe `categories.json` no componente/seed de categorias do seu projeto e aplique `event-space-filters.json` no formulário de publicação e na pesquisa da categoria de eventos.
