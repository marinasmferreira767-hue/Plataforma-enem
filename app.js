/* ═══════════════════════════════════════════════════════════════════════════
   NOTA MIL — camada de interface
   SPA sem framework: roteador por hash, views em template literal e
   gráficos desenhados em SVG na mão.
   ═══════════════════════════════════════════════════════════════════════════ */

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const estado = {
  token: localStorage.getItem('nm_token'),
  usuario: null,
  iaAtiva: false,
  questoes: [],
  qIndice: 0,
  qMarcada: null,
  qResultado: null,
  qInicio: 0,
  filtros: { disciplina: 'Todas', ano: null, naoRespondidas: false },
  ultimaCorrecao: null,
};

const COMPETENCIAS = {
  1: 'Domínio da norma culta',
  2: 'Compreender o tema e aplicar repertório',
  3: 'Selecionar e organizar argumentos',
  4: 'Coesão e mecanismos linguísticos',
  5: 'Proposta de intervenção',
};

const TEMAS_SUGERIDOS = [
  'Desafios para a valorização da leitura no Brasil contemporâneo',
  'Caminhos para combater a desinformação nas redes sociais',
  'O impacto da inteligência artificial no mercado de trabalho brasileiro',
  'A permanência da desigualdade de acesso ao saneamento básico no Brasil',
  'Saúde mental na adolescência: um desafio para a escola brasileira',
];


/* ═══ UTILIDADES ══════════════════════════════════════════════════════════ */

const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function dataBR(iso) {
  if (!iso) return '';
  const [d, h] = iso.split(' ');
  const [a, m, dia] = d.split('-');
  return `${dia}/${m}/${a}${h ? ' às ' + h.slice(0, 5) : ''}`;
}

async function api(caminho, opcoes = {}) {
  const cab = { 'Content-Type': 'application/json', ...(opcoes.headers || {}) };
  if (estado.token) cab.Authorization = `Bearer ${estado.token}`;

  const resp = await fetch(`/api${caminho}`, { ...opcoes, headers: cab });

  if (resp.status === 401 && estado.token) {
    sair(true);
    throw new Error('Sessão expirada. Entre novamente.');
  }
  const corpo = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(corpo.erro || corpo.detail || 'Algo deu errado na requisição.');
  return corpo;
}

function toast(mensagem, tipo = '') {
  const el = document.createElement('div');
  el.className = `toast ${tipo ? 'toast--' + tipo : ''}`;
  el.innerHTML = `<span class="toast__barra"></span><span>${esc(mensagem)}</span>`;
  $('#toasts').appendChild(el);
  setTimeout(() => {
    el.classList.add('is-saindo');
    setTimeout(() => el.remove(), 260);
  }, 4200);
}

/* markdown mínimo: negrito, listas e parágrafos */
function md(texto) {
  const linhas = esc(texto).split('\n');
  let saida = '', emLista = false;
  for (let l of linhas) {
    l = l.trim();
    l = l.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
         .replace(/`(.+?)`/g, '<code>$1</code>');
    if (/^[-*•]\s+/.test(l)) {
      if (!emLista) { saida += '<ul>'; emLista = true; }
      saida += `<li>${l.replace(/^[-*•]\s+/, '')}</li>`;
      continue;
    }
    if (emLista) { saida += '</ul>'; emLista = false; }
    if (l) saida += `<p>${l}</p>`;
  }
  if (emLista) saida += '</ul>';
  return saida;
}

function animarNumero(el, ate, duracao = 900) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { el.textContent = ate; return; }
  const t0 = performance.now();
  const passo = (t) => {
    const p = Math.min(1, (t - t0) / duracao);
    el.textContent = Math.round(ate * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(passo);
  };
  requestAnimationFrame(passo);
}

function faixa(nota) {
  if (nota >= 900) return 'Nível excelente';
  if (nota >= 800) return 'Muito bom';
  if (nota >= 600) return 'No caminho certo';
  if (nota >= 400) return 'Em desenvolvimento';
  return 'Começando agora';
}

function corNota(nota, max = 1000) {
  const p = nota / max;
  if (p >= 0.8) return 'var(--verde)';
  if (p >= 0.6) return 'var(--azul-claro)';
  if (p >= 0.4) return 'var(--amarelo)';
  return 'var(--vermelho)';
}


/* ═══ AUTENTICAÇÃO ════════════════════════════════════════════════════════ */

function montarTabsAuth() {
  const btns = $$('.tabs__btn');
  const ink = $('.tabs__ink');
  const mover = (btn) => {
    ink.style.width = `${btn.offsetWidth}px`;
    ink.style.transform = `translateX(${btn.offsetLeft}px)`;
  };
  btns.forEach((b) => b.addEventListener('click', () => {
    btns.forEach((x) => x.classList.toggle('is-on', x === b));
    $('#form-login').hidden = b.dataset.tab !== 'login';
    $('#form-cadastro').hidden = b.dataset.tab !== 'cadastro';
    mover(b);
  }));
  requestAnimationFrame(() => mover(btns[0]));
  addEventListener('resize', () => mover($('.tabs__btn.is-on')));
}

function forcaSenha(s) {
  let f = 0;
  if (s.length >= 6) f++;
  if (s.length >= 10) f++;
  if (/[A-Z]/.test(s) && /[a-z]/.test(s)) f++;
  if (/\d/.test(s) || /[^\w]/.test(s)) f++;
  return f;
}

function ligarFormularios() {
  const senhaCad = $('#form-cadastro input[name=senha]');
  const barra = $('#form-cadastro [data-meter] i');
  senhaCad.addEventListener('input', () => {
    const f = forcaSenha(senhaCad.value);
    barra.style.width = `${(f / 4) * 100}%`;
    barra.style.background = ['var(--vermelho)', 'var(--vermelho)', 'var(--amarelo)', 'var(--verde)', 'var(--verde)'][f];
  });

  const enviar = async (form, rota, montarCorpo) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = $('button[type=submit]', form);
      const erro = $('[data-erro]', form);
      erro.hidden = true;
      btn.classList.add('is-carregando');
      try {
        const dados = await api(rota, { method: 'POST', body: JSON.stringify(montarCorpo(form)) });
        estado.token = dados.token;
        estado.usuario = dados.usuario;
        localStorage.setItem('nm_token', dados.token);
        await iniciarApp();
        toast(`Boa, ${dados.usuario.nome.split(' ')[0]}. Bons estudos.`, 'ok');
      } catch (err) {
        erro.textContent = err.message;
        erro.hidden = false;
      } finally {
        btn.classList.remove('is-carregando');
      }
    });
  };

  enviar($('#form-login'), '/auth/login', (f) => ({
    email: f.email.value.trim(), senha: f.senha.value,
  }));
  enviar($('#form-cadastro'), '/auth/cadastro', (f) => ({
    nome: f.nome.value.trim(), email: f.email.value.trim(), senha: f.senha.value,
  }));
}

async function sair(silencioso = false) {
  try { await api('/auth/logout', { method: 'POST' }); } catch { /* sessão já morta */ }
  localStorage.removeItem('nm_token');
  estado.token = null;
  estado.usuario = null;
  $('#shell').hidden = true;
  $('#auth').hidden = false;
  if (!silencioso) toast('Você saiu da conta.');
}


/* ═══ NAVEGAÇÃO ═══════════════════════════════════════════════════════════ */

function fecharGaveta() {
  $('#nav').classList.remove('is-aberto');
  $('#scrim').hidden = true;
}

function ligarNavegacao() {
  $('#btn-menu').addEventListener('click', () => {
    $('#nav').classList.add('is-aberto');
    $('#scrim').hidden = false;
  });
  $('#scrim').addEventListener('click', fecharGaveta);
  $('#btn-sair').addEventListener('click', () => sair());
  addEventListener('hashchange', rotear);
  addEventListener('keydown', (e) => { if (e.key === 'Escape') fecharGaveta(); });

  $$('.nav__links a').forEach((a) => {
    a.dataset.dica = a.querySelector('span').textContent;
    a.addEventListener('click', fecharGaveta);
  });
}

const ROTAS = {
  inicio: viewInicio,
  redacao: viewRedacao,
  simulado: viewSimulado,
  gerar: viewGerar,
  historico: viewHistorico,
  desempenho: viewDesempenho,
};

async function rotear() {
  const nome = (location.hash.replace('#/', '') || 'inicio').split('?')[0];
  const view = ROTAS[nome] || viewInicio;

  $$('[data-rota]').forEach((a) => a.classList.toggle('is-on', a.dataset.rota === nome));

  const app = $('#app');
  app.innerHTML = '';
  app.style.animation = 'none';
  void app.offsetWidth;
  app.style.animation = '';
  scrollTo({ top: 0, behavior: 'instant' });

  try {
    await view(app);
  } catch (err) {
    app.innerHTML = `<div class="vazio">
      <div class="vazio__icone"><svg viewBox="0 0 24 24"><path d="M12 8v5m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg></div>
      <h3>Não deu para carregar esta página</h3>
      <p>${esc(err.message)}</p>
      <button class="btn btn--ghost" onclick="location.reload()">Tentar de novo</button>
    </div>`;
  }
}


/* ═══ GRÁFICOS EM SVG ═════════════════════════════════════════════════════ */

/* anel de nota: 5 arcos, um por competência */
function anelNota(notaFinal, competencias) {
  const R = 78, C = 95, ESP = 13, VAO = 5;
  const total = 360 / 5;
  const arco = (i, frac, cor, op) => {
    const ini = -90 + i * total + VAO / 2;
    const fim = ini + (total - VAO) * frac;
    const p = (ang) => [C + R * Math.cos(ang * Math.PI / 180), C + R * Math.sin(ang * Math.PI / 180)];
    const [x1, y1] = p(ini), [x2, y2] = p(fim);
    if (frac <= 0.001) return '';
    const grande = (total - VAO) * frac > 180 ? 1 : 0;
    return `<path d="M${x1} ${y1} A${R} ${R} 0 ${grande} 1 ${x2} ${y2}"
             fill="none" stroke="${cor}" stroke-width="${ESP}" stroke-linecap="round" opacity="${op}"/>`;
  };

  const fundo = competencias.map((_, i) => arco(i, 1, 'var(--mesa-700)', 1)).join('');
  const frente = competencias.map((c, i) =>
    arco(i, Math.max(c.nota / 200, 0.0001), corNota(c.nota, 200), 1)).join('');

  return `<svg class="anel" viewBox="0 0 190 190" role="img" aria-label="Nota ${notaFinal} de 1000">
    ${fundo}${frente}
    <text class="anel__num" x="95" y="98" text-anchor="middle" data-contador>0</text>
    <text class="anel__max" x="95" y="120" text-anchor="middle">/ 1000</text>
  </svg>`;
}

/* radar pentagonal das competências */
function radarCompetencias(comps) {
  const C = 150, R = 105, N = 5;
  const ponto = (i, raio) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / N;
    return [C + raio * Math.cos(a), C + raio * Math.sin(a)];
  };
  const poligono = (raio, extra = '') =>
    `<polygon points="${[...Array(N)].map((_, i) => ponto(i, raio).join(',')).join(' ')}" ${extra}/>`;

  const teias = [0.25, 0.5, 0.75, 1]
    .map((f) => poligono(R * f, 'fill="none" stroke="var(--linha)" stroke-width="1"')).join('');
  const eixos = [...Array(N)].map((_, i) => {
    const [x, y] = ponto(i, R);
    return `<line x1="${C}" y1="${C}" x2="${x}" y2="${y}" stroke="var(--linha)" stroke-width="1"/>`;
  }).join('');

  const pontos = comps.map((c, i) => ponto(i, R * Math.max(c.media / 200, 0.04)).join(',')).join(' ');
  const bolinhas = comps.map((c, i) => {
    const [x, y] = ponto(i, R * Math.max(c.media / 200, 0.04));
    return `<circle cx="${x}" cy="${y}" r="4.5" fill="var(--azul-claro)"/>`;
  }).join('');
  const rotulos = comps.map((c, i) => {
    const [x, y] = ponto(i, R + 26);
    return `<text x="${x}" y="${y}" text-anchor="middle" dominant-baseline="middle"
             font-family="var(--f-mono)" font-size="15" font-weight="700" fill="var(--txt-2)">C${c.numero}</text>
            <text x="${x}" y="${y + 18}" text-anchor="middle" dominant-baseline="middle"
             font-size="13" fill="var(--txt-3)">${c.media}</text>`;
  }).join('');

  return `<svg viewBox="0 0 300 300" role="img" aria-label="Média por competência">
    ${teias}${eixos}
    <polygon points="${pontos}" fill="rgba(61,90,254,.28)" stroke="var(--azul)" stroke-width="2.5"
      stroke-linejoin="round"/>
    ${bolinhas}${rotulos}
  </svg>`;
}

/* linha de evolução das notas */
function linhaEvolucao(pontos) {
  const L = 620, A = 260, pad = { t: 20, r: 20, b: 44, e: 60 };
  const notas = pontos.map((p) => p.nota);
  const min = Math.max(0, Math.min(...notas) - 120);
  const max = Math.min(1000, Math.max(...notas) + 120);
  const px = (i) => pad.e + (i * (L - pad.e - pad.r)) / Math.max(1, pontos.length - 1);
  const py = (v) => pad.t + (1 - (v - min) / (max - min || 1)) * (A - pad.t - pad.b);

  const grade = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = Math.round(min + f * (max - min));
    const y = py(v);
    return `<line x1="${pad.e}" y1="${y}" x2="${L - pad.r}" y2="${y}" stroke="var(--linha)" stroke-width="1"/>
            <text x="${pad.e - 12}" y="${y + 7}" text-anchor="end" font-family="var(--f-mono)"
              font-size="18" fill="var(--txt-3)">${v}</text>`;
  }).join('');

  const d = pontos.map((p, i) => `${i ? 'L' : 'M'}${px(i)} ${py(p.nota)}`).join(' ');
  const area = `${d} L${px(pontos.length - 1)} ${A - pad.b} L${px(0)} ${A - pad.b} Z`;
  const marcas = pontos.map((p, i) => `
    <circle cx="${px(i)}" cy="${py(p.nota)}" r="7" fill="var(--mesa-850)" stroke="var(--azul)" stroke-width="3">
      <title>Correção ${p.n}: ${p.nota} pontos (${dataBR(p.data)})</title></circle>
    <text x="${px(i)}" y="${A - 12}" text-anchor="middle" font-size="16" fill="var(--txt-3)" font-family="var(--f-mono)">#${p.n}</text>`).join('');

  return `<svg viewBox="0 0 ${L} ${A}" role="img" aria-label="Evolução das notas" preserveAspectRatio="xMidYMid meet">
    <defs><linearGradient id="gArea" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="var(--azul)" stop-opacity=".34"/>
      <stop offset="100%" stop-color="var(--azul)" stop-opacity="0"/>
    </linearGradient></defs>
    ${grade}
    <path d="${area}" fill="url(#gArea)"/>
    <path d="${d}" fill="none" stroke="var(--azul)" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
    ${marcas}
  </svg>`;
}


/* ═══ VIEW: INÍCIO ════════════════════════════════════════════════════════ */

function diasAteEnem() {
  const hoje = new Date();
  const anos = [hoje.getFullYear(), hoje.getFullYear() + 1];
  // ENEM cai no primeiro domingo de novembro; aproximação boa o bastante
  for (const y of anos) {
    const nov = new Date(y, 10, 1);
    const domingo1 = new Date(y, 10, 1 + ((7 - nov.getDay()) % 7));
    const diff = Math.ceil((domingo1 - hoje) / 86400000);
    if (diff >= 0) return { dias: diff, data: domingo1 };
  }
}

async function viewInicio(app) {
  const primeiro = estado.usuario.nome.split(' ')[0];
  const enem = diasAteEnem();

  app.innerHTML = `
    <div class="hero mb-3">
      <div class="hero__conteudo">
        <span class="olho">Painel do aluno</span>
        <h1 class="pagina__titulo">Bom te ver, ${esc(primeiro)}.</h1>
        <p class="pagina__sub">Escolha por onde continuar hoje. Cada redação corrigida e cada
        questão respondida alimentam o seu painel de desempenho.</p>
      </div>
      <div class="hero__contagem" title="Data aproximada do primeiro dia de prova">
        <span class="hero__contagem-num" data-conta="${enem.dias}">0</span>
        <span class="hero__contagem-lbl">dias até o ENEM</span>
        <span class="hero__contagem-data">${enem.data.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long' })}</span>
      </div>
    </div>

    <div class="grade grade--4 mb-3" id="stats">
      ${'<div class="esq esq--bloco" style="height:112px"></div>'.repeat(4)}
    </div>

    <div class="grade grade--12 mb-3">
      <button class="acao acao--grande span-6" data-ir="#/redacao">
        <span class="acao__icone"><svg viewBox="0 0 24 24"><path d="M4 20h4l10-10-4-4L4 16zM14 4l4 4 2-2-4-4z"/></svg></span>
        <h3>Corrigir uma redação</h3>
        <p>Nota por competência, comentários com trechos do seu texto e reescritas prontas para comparar.</p>
        <span class="acao__seta">Escrever agora →</span>
      </button>
      <button class="acao acao--amarelo span-3" data-ir="#/simulado">
        <span class="acao__icone"><svg viewBox="0 0 24 24"><path d="M5 3h14v18l-7-4-7 4z"/></svg></span>
        <h3>Treinar questões</h3>
        <p>Cartão-resposta interativo e explicação passo a passo.</p>
        <span class="acao__seta">Abrir simulado →</span>
      </button>
      <button class="acao acao--roxo span-3" data-ir="#/gerar">
        <span class="acao__icone"><svg viewBox="0 0 24 24"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/></svg></span>
        <h3>Gerar com IA</h3>
        <p>Diga o tópico e a IA cria questões inéditas para você.</p>
        <span class="acao__seta">Criar agora →</span>
      </button>
    </div>

    <div class="grade grade--12">
      <div class="cartao span-8">
        <div class="linha-flex entre mb-2">
          <div>
            <h3 class="cartao__titulo">Onde você mais perde ponto</h3>
            <p class="cartao__texto">A competência com a menor média nas suas últimas redações.</p>
          </div>
          <a href="#/desempenho" class="btn btn--ghost btn--sm">Ver relatório completo</a>
        </div>
        <div id="fraca">${'<div class="esq esq--linha" style="width:70%"></div>'.repeat(3)}</div>
      </div>
      <div class="cartao span-4">
        <h3 class="cartao__titulo">Sequência de estudos</h3>
        <p class="cartao__texto">Dias seguidos treinando na plataforma.</p>
        <div class="streak" id="streak">
          <span class="streak__num" data-conta="0">0</span>
          <span class="streak__lbl">dias seguidos</span>
        </div>
      </div>
    </div>

    ${estado.iaAtiva ? '' : `
      <div class="bloco bloco--atencao mt-3">
        <h4>⚠ Recursos de IA desativados</h4>
        <p style="color:var(--txt-2);font-size:.92rem">Nenhuma chave de API foi encontrada no servidor.
        Login, simulados, gabaritos e histórico seguem funcionando; a correção de redação e
        a geração de questões ficam indisponíveis até configurar <code>ANTHROPIC_API_KEY</code>
        ou <code>OPENAI_API_KEY</code>.</p>
      </div>`}
  `;

  $$('[data-ir]', app).forEach((b) =>
    b.addEventListener('click', () => { location.hash = b.dataset.ir; }));

  const d = await api('/desempenho');
  $('#stats').innerHTML = `
    <div class="stat"><div class="stat__k" data-conta="${d.redacoes}">0</div><div class="stat__l">Redações corrigidas</div></div>
    <div class="stat stat--amarelo"><div class="stat__k" data-conta="${d.media_redacao}">0</div><div class="stat__l">Média das redações</div></div>
    <div class="stat"><div class="stat__k" data-conta="${d.questoes}">0</div><div class="stat__l">Questões respondidas</div></div>
    <div class="stat stat--verde"><div class="stat__k">${d.taxa_acerto}<span style="font-size:1.1rem">%</span></div><div class="stat__l">Taxa de acerto</div></div>`;

  $('#streak').innerHTML = `
    <span class="streak__num" data-conta="${d.streak || 0}">0</span>
    <span class="streak__lbl">${(d.streak || 0) === 1 ? 'dia seguido' : 'dias seguidos'}</span>
    <p class="streak__ajuda">${d.streak > 0
      ? 'Volte amanhã para manter a sequência.'
      : 'Responda uma questão hoje para começar a contar.'}</p>`;

  if (d.competencia_fraca && d.redacoes > 0) {
    const f = d.competencia_fraca;
    $('#fraca').innerHTML = `
      <div class="fraca">
        <div class="fraca__marca">C${f.numero}</div>
        <div class="fraca__meio">
          <div class="fraca__titulo">${esc(f.titulo)}</div>
          <div class="fraca__barra"><i style="width:${(f.media / 200) * 100}%"></i></div>
        </div>
        <div class="fraca__nota">${f.media}<small>/200</small></div>
      </div>
      <p class="cartao__texto mt-2">Concentre a próxima redação nesta competência para
      recuperar o maior número de pontos com o menor esforço.</p>`;
  } else {
    $('#fraca').innerHTML = `
      <div class="vazio vazio--pequeno">
        <p>Corrija sua primeira redação para descobrir onde você mais perde ponto.</p>
        <button class="btn btn--primary" onclick="location.hash='#/redacao'">Corrigir minha primeira redação</button>
      </div>`;
  }

  $$('[data-conta]', app).forEach((el) => animarNumero(el, +el.dataset.conta));
}


/* ═══ VIEW: REDAÇÃO ═══════════════════════════════════════════════════════ */

async function viewRedacao(app) {
  app.innerHTML = `
    <div class="pagina__topo">
      <span class="olho">Módulo 1 · Corretor</span>
      <h1 class="pagina__titulo">Corretor de redação</h1>
      <p class="pagina__sub">A banca de IA aplica a matriz do INEP, aponta os trechos que custam
      ponto e devolve sugestões de reescrita. Sua correção fica salva no histórico.</p>
    </div>

    <div class="temas" id="temas"></div>

    <form id="form-redacao">
      <div class="editor">
        <input class="editor__tema" name="tema" maxlength="300" required
               placeholder="Tema da redação — ex.: Desafios para a valorização da leitura no Brasil">
        <textarea class="editor__corpo" name="texto" required
          placeholder="Escreva ou cole sua redação aqui, com introdução, desenvolvimento e conclusão…"></textarea>
        <div class="editor__pe">
          <span class="contador" id="contador"><b>0</b> palavras · <b>0</b> linhas</span>
          <span style="flex:1"></span>
          <button type="button" class="btn btn--sm btn--ghost" id="btn-limpar">Limpar</button>
          <button type="submit" class="btn btn--primary" id="btn-corrigir">Corrigir com IA</button>
        </div>
      </div>
    </form>

    <div id="resultado" class="mt-3"></div>
  `;

  $('#temas').innerHTML = TEMAS_SUGERIDOS
    .map((t) => `<button class="tema-sugerido" type="button">${esc(t)}</button>`).join('');
  $$('.tema-sugerido', app).forEach((b) => b.addEventListener('click', () => {
    $('[name=tema]').value = b.textContent;
    $('[name=texto]').focus();
  }));

  const texto = $('[name=texto]');
  const contador = $('#contador');
  const atualizar = () => {
    const palavras = texto.value.trim() ? texto.value.trim().split(/\s+/).length : 0;
    const linhas = texto.value.trim() ? texto.value.trim().split('\n').filter(Boolean).length : 0;
    contador.innerHTML = `<b>${palavras}</b> palavras · <b>${linhas}</b> parágrafos`;
    contador.classList.toggle('is-ok', palavras >= 150);
  };
  texto.addEventListener('input', atualizar);

  $('#btn-limpar').addEventListener('click', () => {
    if (!texto.value || confirm('Apagar o texto escrito?')) {
      texto.value = ''; $('[name=tema]').value = ''; atualizar(); $('#resultado').innerHTML = '';
    }
  });

  $('#form-redacao').addEventListener('submit', async (e) => {
    e.preventDefault();
    const tema = $('[name=tema]').value.trim();
    const corpo = texto.value.trim();

    if (tema.length < 5) return toast('Escreva o tema da redação antes de corrigir.', 'erro');
    if (corpo.split(/\s+/).length < 50) return toast('A redação precisa ter pelo menos 50 palavras.', 'erro');
    if (!estado.iaAtiva) return toast('Correção por IA indisponível: falta a chave de API no servidor.', 'erro');

    const btn = $('#btn-corrigir');
    btn.classList.add('is-carregando');
    $('#resultado').innerHTML = `
      <div class="cartao">
        <div class="pensando">
          <span class="pensando__pontos"><i></i><i></i><i></i></span>
          A banca está lendo sua redação e avaliando as cinco competências…
        </div>
        <div class="esq esq--linha" style="width:70%"></div>
        <div class="esq esq--linha" style="width:92%"></div>
        <div class="esq esq--linha" style="width:55%"></div>
      </div>`;

    try {
      const r = await api('/redacoes', { method: 'POST', body: JSON.stringify({ tema, texto: corpo }) });
      estado.ultimaCorrecao = r;
      renderCorrecao($('#resultado'), r);
      toast(`Correção concluída: ${r.nota_final} pontos. Salva no histórico.`, 'ok');
      $('#resultado').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      $('#resultado').innerHTML = '';
      toast(err.message, 'erro');
    } finally {
      btn.classList.remove('is-carregando');
    }
  });
}

function renderCorrecao(alvo, r) {
  alvo.innerHTML = `
    <div class="placar mb-3">
      ${anelNota(r.nota_final, r.competencias)}
      <div class="placar__lado">
        <div class="placar__faixa" style="color:${corNota(r.nota_final)}">${faixa(r.nota_final)}</div>
        <p class="placar__tema">${esc(r.tema || '')}</p>
        ${r.competencias.map((c) => `
          <div class="comp">
            <div class="comp__topo">
              <span class="comp__nome">Competência ${c.numero}<i>${esc(c.titulo || COMPETENCIAS[c.numero])}</i></span>
              <span class="comp__nota" style="color:${corNota(c.nota, 200)}">${c.nota}<span style="color:var(--txt-3);font-size:.8em">/200</span></span>
            </div>
            <div class="comp__barra"><i data-largura="${(c.nota / 200) * 100}"></i></div>
          </div>`).join('')}
      </div>
    </div>

    ${r.resumo ? `<div class="bloco bloco--info mb-2"><h4>Diagnóstico geral</h4>
      <p style="color:var(--txt-2);font-size:.93rem;line-height:1.65">${esc(r.resumo)}</p></div>` : ''}

    <div class="grade grade--2 mb-3">
      ${r.pontos_fortes?.length ? `<div class="bloco bloco--ok"><h4>O que já está funcionando</h4>
        <ul>${r.pontos_fortes.map((p) => `<li>${esc(p)}</li>`).join('')}</ul></div>` : ''}
      ${r.pontos_a_melhorar?.length ? `<div class="bloco bloco--atencao"><h4>O que atacar na próxima</h4>
        <ul>${r.pontos_a_melhorar.map((p) => `<li>${esc(p)}</li>`).join('')}</ul></div>` : ''}
    </div>

    <div class="cartao mb-3">
      <h3 class="cartao__titulo">Comentário da banca, competência por competência</h3>
      <p class="cartao__texto mb-2">Cada nota abaixo vem acompanhada da justificativa técnica.</p>
      ${r.competencias.map((c) => `
        <div class="comp">
          <div class="comp__topo">
            <span class="comp__nome">C${c.numero} — ${esc(c.titulo || COMPETENCIAS[c.numero])}</span>
            <span class="comp__nota" style="color:${corNota(c.nota, 200)}">${c.nota}</span>
          </div>
          <p class="comp__coment">${esc(c.comentario)}</p>
        </div>`).join('')}
    </div>

    ${r.reescritas?.length ? `
      <div class="papel">
        <span class="papel__margem"></span>
        <h3 style="font-size:1.2rem;margin-bottom:.4rem">Sugestões de reescrita</h3>
        <p style="color:var(--papel-tinta-2);font-size:.9rem;margin-bottom:1.3rem">
          Compare o que você escreveu com a versão sugerida e entenda a diferença.</p>
        ${r.reescritas.map((s) => `
          <div class="reescrita">
            <div class="reescrita__linha">
              <span class="reescrita__tag reescrita__tag--antes">antes</span>
              <span class="reescrita__antes">${esc(s.trecho_original)}</span>
            </div>
            <div class="reescrita__linha">
              <span class="reescrita__tag reescrita__tag--depois">depois</span>
              <span>${esc(s.sugestao)}</span>
            </div>
            <p class="reescrita__motivo">${esc(s.motivo)}</p>
          </div>`).join('')}
      </div>` : ''}
  `;

  const num = $('[data-contador]', alvo);
  if (num) animarNumero(num, r.nota_final, 1100);
  requestAnimationFrame(() => {
    $$('[data-largura]', alvo).forEach((b, i) => {
      setTimeout(() => { b.style.width = `${b.dataset.largura}%`; }, 90 * i);
    });
  });
}


/* ═══ VIEW: SIMULADO ══════════════════════════════════════════════════════ */

async function viewSimulado(app) {
  app.innerHTML = `
    <div class="pagina__topo">
      <span class="olho">Módulo 2 · Banco de questões</span>
      <h1 class="pagina__titulo">Simulado</h1>
      <p class="pagina__sub">Marque a alternativa no cartão-resposta e confirme. Você pode usar
      as teclas <b>A</b> a <b>E</b> para marcar e <b>Enter</b> para confirmar.</p>
    </div>
    <div class="cartao cartao--liso mb-2" style="padding:0">
      <div class="chips mb-2" id="filtro-disc"></div>
      <div class="linha-flex entre">
        <label class="switch">
          <input type="checkbox" id="f-novas"><i></i>
          <span>Só questões que ainda não respondi</span>
        </label>
        <span class="chip" id="contagem">—</span>
      </div>
    </div>
    <div id="palco"></div>
  `;

  const filtros = await api('/questoes/filtros');
  $('#filtro-disc').innerHTML = ['Todas', ...filtros.disciplinas]
    .map((d) => `<button class="filtro ${d === estado.filtros.disciplina ? 'is-on' : ''}" data-disc="${esc(d)}">${esc(d)}</button>`)
    .join('');

  $$('[data-disc]', app).forEach((b) => b.addEventListener('click', () => {
    estado.filtros.disciplina = b.dataset.disc;
    $$('[data-disc]', app).forEach((x) => x.classList.toggle('is-on', x === b));
    carregarQuestoes();
  }));

  $('#f-novas').checked = estado.filtros.naoRespondidas;
  $('#f-novas').addEventListener('change', (e) => {
    estado.filtros.naoRespondidas = e.target.checked;
    carregarQuestoes();
  });

  await carregarQuestoes();
}

async function carregarQuestoes() {
  const palco = $('#palco');
  palco.innerHTML = `<div class="papel"><div class="esq esq--linha" style="width:85%"></div>
    <div class="esq esq--linha" style="width:96%"></div>
    <div class="esq esq--linha" style="width:60%;margin-bottom:1.6rem"></div>
    ${'<div class="esq esq--linha" style="height:46px"></div>'.repeat(5)}</div>`;

  const p = new URLSearchParams();
  if (estado.filtros.disciplina !== 'Todas') p.set('disciplina', estado.filtros.disciplina);
  if (estado.filtros.naoRespondidas) p.set('nao_respondidas', 'true');

  const dados = await api(`/questoes?${p}`);
  estado.questoes = dados.questoes;
  estado.qIndice = 0;
  $('#contagem').textContent = `${dados.total} questões`;
  renderQuestao();
}

function renderQuestao() {
  const palco = $('#palco');
  const q = estado.questoes[estado.qIndice];

  if (!q) {
    palco.innerHTML = `<div class="vazio">
      <div class="vazio__icone"><svg viewBox="0 0 24 24"><path d="M5 3h14v18l-7-4-7 4z"/></svg></div>
      <h3>Nenhuma questão neste filtro</h3>
      <p>Troque a disciplina acima ou importe novas provas rodando
      <code>python extrair_questoes.py</code> com os PDFs na pasta <code>questoes_pdf/</code>.</p>
      <button class="btn btn--ghost" onclick="location.reload()">Recarregar</button>
    </div>`;
    return;
  }

  estado.qMarcada = null;
  estado.qResultado = null;
  estado.qInicio = Date.now();

  palco.innerHTML = `
    <div class="linha-flex mb-2">
      <span class="chip chip--azul">${estado.qIndice + 1} de ${estado.questoes.length}</span>
      <span class="chip">${esc(q.disciplina)}</span>
      ${q.prova ? `<span class="chip">${esc(q.prova)}${q.ano ? ' · ' + q.ano : ''}</span>` : ''}
      ${q.ja_respondida ? '<span class="chip chip--amarelo">já respondida</span>' : ''}
    </div>

    <div class="papel">
      <span class="papel__margem"></span>
      <div class="enunciado">${esc(q.enunciado)}</div>
      <div class="opcoes" id="opcoes">
        ${q.alternativas.map((a) => `
          <button class="opcao" data-letra="${a.letra}">
            <span class="bolha"><span>${a.letra}</span></span>
            <span class="opcao__txt">${esc(a.texto)}</span>
          </button>`).join('')}
      </div>
    </div>

    <div id="feedback" class="mt-2"></div>

    <div class="linha-flex entre mt-2">
      <button class="btn btn--ghost btn--sm" id="btn-anterior" ${estado.qIndice === 0 ? 'disabled' : ''}>← Anterior</button>
      <div class="linha-flex">
        <button class="btn btn--ghost btn--sm" id="btn-pular">Pular</button>
        <button class="btn btn--primary" id="btn-confirmar" disabled>Confirmar resposta</button>
      </div>
    </div>
  `;

  $$('#opcoes .opcao').forEach((b) => b.addEventListener('click', () => marcar(b.dataset.letra)));
  $('#btn-confirmar').addEventListener('click', confirmarResposta);
  $('#btn-pular').addEventListener('click', proximaQuestao);
  $('#btn-anterior').addEventListener('click', () => {
    if (estado.qIndice > 0) { estado.qIndice--; renderQuestao(); }
  });
}

function marcar(letra) {
  if (estado.qResultado) return;
  estado.qMarcada = letra;
  $$('#opcoes .opcao').forEach((b) => b.classList.toggle('is-marcada', b.dataset.letra === letra));
  $('#btn-confirmar').disabled = false;
}

async function confirmarResposta() {
  if (!estado.qMarcada || estado.qResultado) return;
  const q = estado.questoes[estado.qIndice];
  const btn = $('#btn-confirmar');
  btn.classList.add('is-carregando');

  try {
    const r = await api(`/questoes/${q.id}/responder`, {
      method: 'POST',
      body: JSON.stringify({
        resposta: estado.qMarcada,
        segundos: Math.round((Date.now() - estado.qInicio) / 1000),
      }),
    });
    estado.qResultado = r;

    $$('#opcoes .opcao').forEach((b) => {
      b.disabled = true;
      b.classList.remove('is-marcada');
      if (b.dataset.letra === r.gabarito) b.classList.add('is-certa');
      else if (b.dataset.letra === r.sua_resposta) b.classList.add('is-errada');
    });

    btn.remove();
    $('#btn-pular').textContent = 'Próxima questão →';
    $('#btn-pular').className = 'btn btn--primary';

    $('#feedback').innerHTML = `
      <div class="veredito ${r.acertou ? 'veredito--ok' : 'veredito--erro'}">
        <span class="veredito__icone">
          <svg viewBox="0 0 24 24">${r.acertou ? '<path d="M4 12l5 5L20 6"/>' : '<path d="M6 6l12 12M18 6L6 18"/>'}</svg>
        </span>
        <span>${r.acertou ? 'Resposta certa.' : `Não foi dessa vez. O gabarito é ${r.gabarito}.`}
          <small>${r.acertou ? `Gabarito ${r.gabarito}, exatamente o que você marcou.`
                             : `Você marcou ${r.sua_resposta}. Leia a explicação abaixo antes de seguir.`}</small></span>
      </div>
      <div class="cartao" id="caixa-explicacao">
        <h3 class="cartao__titulo">Explicação do professor de IA</h3>
        <div id="explicacao" class="mt-1"></div>
      </div>`;

    carregarExplicacao(q.id);
    $('#feedback').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (err) {
    toast(err.message, 'erro');
  } finally {
    btn.classList?.remove('is-carregando');
  }
}

async function carregarExplicacao(qid) {
  const alvo = $('#explicacao');
  if (!alvo) return;

  if (!estado.iaAtiva) {
    alvo.innerHTML = `<p class="cartao__texto">As explicações por IA estão desativadas:
      falta configurar a chave de API no servidor.</p>`;
    return;
  }

  alvo.innerHTML = `<div class="pensando">
    <span class="pensando__pontos"><i></i><i></i><i></i></span>
    Montando a resolução passo a passo…</div>`;

  try {
    const r = await api(`/questoes/${qid}/explicacao`);
    alvo.innerHTML = `<div class="md">${md(r.texto)}</div>`;
  } catch (err) {
    alvo.innerHTML = `<p class="cartao__texto">Não deu para gerar a explicação agora: ${esc(err.message)}</p>`;
  }
}

function proximaQuestao() {
  if (estado.qIndice < estado.questoes.length - 1) {
    estado.qIndice++;
    renderQuestao();
    $('#palco').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } else {
    toast('Você chegou ao fim desta lista. Troque o filtro para continuar.', 'ok');
  }
}

/* atalhos de teclado no simulado */
addEventListener('keydown', (e) => {
  if (!location.hash.includes('simulado')) return;
  if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

  const letra = e.key.toUpperCase();
  if ('ABCDE'.includes(letra) && letra.length === 1) { marcar(letra); e.preventDefault(); }
  if (e.key === 'Enter') {
    if (estado.qResultado) proximaQuestao();
    else if (estado.qMarcada) confirmarResposta();
  }
  if (e.key === 'ArrowRight' && estado.qResultado) proximaQuestao();
});


/* ═══ VIEW: GERAR QUESTÕES COM IA ═════════════════════════════════════════ */

const DISCIPLINAS_GERADOR = [
  'Matemática', 'Física', 'Química', 'Biologia',
  'Português', 'Literatura', 'Redação', 'Inglês', 'Espanhol',
  'História', 'Geografia', 'Sociologia', 'Filosofia',
];

const SUGESTOES_TOPICO = {
  'Matemática': ['Funções do 2º grau', 'Progressão geométrica', 'Probabilidade condicional', 'Análise combinatória'],
  'Física': ['Leis de Newton', 'Termodinâmica: 1ª lei', 'Óptica geométrica', 'Circuitos elétricos'],
  'Química': ['Estequiometria', 'Equilíbrio químico', 'Química orgânica: funções', 'Cinética química'],
  'Biologia': ['Genética mendeliana', 'Ecologia: ciclos biogeoquímicos', 'Sistema imunológico', 'Fotossíntese'],
  'Português': ['Regência verbal', 'Concordância verbal', 'Funções da linguagem', 'Figuras de linguagem'],
  'História': ['Era Vargas', 'Ditadura militar no Brasil', 'Revolução Industrial', 'Guerra Fria'],
  'Geografia': ['Urbanização brasileira', 'Placas tectônicas', 'Climas do Brasil', 'Globalização'],
  'Sociologia': ['Weber e a burocracia', 'Movimentos sociais', 'Cultura e indústria cultural', 'Cidadania'],
  'Filosofia': ['Filosofia moral de Kant', 'Contrato social', 'Existencialismo', 'Escola de Frankfurt'],
  'Literatura': ['Modernismo brasileiro', 'Machado de Assis', 'Romantismo', 'Barroco'],
  'Inglês': ['Reading comprehension', 'Verb tenses', 'Modal verbs', 'Passive voice'],
  'Espanhol': ['Comprensión lectora', 'Falsos amigos', 'Ser vs estar', 'Pretérito indefinido'],
  'Redação': ['Estrutura dissertativo-argumentativa', 'Coesão referencial', 'Proposta de intervenção'],
};

async function viewGerar(app) {
  app.innerHTML = `
    <div class="pagina__topo">
      <span class="olho">Módulo 3 · Gerador</span>
      <h1 class="pagina__titulo">Questões inéditas com IA</h1>
      <p class="pagina__sub">Diga a matéria e o tópico. A IA cria questões no padrão ENEM
      com gabarito e explicação, e elas ficam disponíveis no seu simulado depois.</p>
    </div>

    <form id="form-gerar" class="cartao">
      <div class="linha-flex" style="flex-wrap:wrap;gap:1rem">
        <label class="field" style="flex:1;min-width:220px">
          <span class="field__label">Matéria</span>
          <select name="disciplina" required>
            ${DISCIPLINAS_GERADOR.map((d) => `<option value="${d}">${d}</option>`).join('')}
          </select>
        </label>
        <label class="field" style="flex:2;min-width:260px">
          <span class="field__label">Tópico</span>
          <input name="topico" required maxlength="200"
                 placeholder="ex.: Equações do 2º grau com discriminante negativo">
        </label>
        <label class="field" style="width:150px">
          <span class="field__label">Quantidade</span>
          <select name="quantidade">
            <option value="1">1 questão</option>
            <option value="3" selected>3 questões</option>
            <option value="5">5 questões</option>
          </select>
        </label>
      </div>

      <div class="sugestoes mt-2" id="sugestoes"></div>

      <div class="linha-flex entre mt-2">
        <p class="cartao__texto" style="margin:0">
          Cada geração leva 15 a 40 segundos e consome créditos da IA.
        </p>
        <button type="submit" class="btn btn--primary" id="btn-gerar">Gerar questões</button>
      </div>
    </form>

    <div id="gerado" class="mt-3"></div>
  `;

  const disc = app.querySelector('[name=disciplina]');
  const topico = app.querySelector('[name=topico]');
  const sug = $('#sugestoes');
  const pintaSugestoes = () => {
    const lista = SUGESTOES_TOPICO[disc.value] || [];
    sug.innerHTML = lista.length
      ? `<span class="sugestoes__lbl">Sugestões:</span>` + lista
          .map((t) => `<button type="button" class="tema-sugerido">${esc(t)}</button>`).join('')
      : '';
    $$('.tema-sugerido', sug).forEach((b) =>
      b.addEventListener('click', () => { topico.value = b.textContent; topico.focus(); }));
  };
  disc.addEventListener('change', pintaSugestoes);
  pintaSugestoes();

  $('#form-gerar').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!estado.iaAtiva) return toast('Geração por IA indisponível: falta a chave de API no servidor.', 'erro');
    if (topico.value.trim().length < 3) return toast('Descreva melhor o tópico da questão.', 'erro');

    const btn = $('#btn-gerar');
    btn.classList.add('is-carregando');
    $('#gerado').innerHTML = `
      <div class="cartao">
        <div class="pensando">
          <span class="pensando__pontos"><i></i><i></i><i></i></span>
          A IA está elaborando questões inéditas sobre <b>${esc(topico.value.trim())}</b>…
        </div>
        ${'<div class="esq esq--linha" style="width:85%"></div><div class="esq esq--linha" style="width:65%"></div>'.repeat(2)}
      </div>`;

    try {
      const r = await api('/questoes/gerar', {
        method: 'POST',
        body: JSON.stringify({
          disciplina: disc.value,
          topico: topico.value.trim(),
          quantidade: +$('[name=quantidade]').value,
        }),
      });
      renderQuestoesGeradas($('#gerado'), r);
      toast(`${r.questoes.length} questões inéditas criadas.`, 'ok');
      $('#gerado').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      $('#gerado').innerHTML = '';
      toast(err.message, 'erro');
    } finally {
      btn.classList.remove('is-carregando');
    }
  });
}

function renderQuestoesGeradas(alvo, r) {
  alvo.innerHTML = `
    <div class="linha-flex entre mb-2">
      <div>
        <h3 style="font-size:1.15rem;margin-bottom:.2rem">Questões geradas · ${esc(r.disciplina)}</h3>
        <p class="cartao__texto" style="margin:0">${esc(r.topico)}</p>
      </div>
      <button class="btn btn--ghost btn--sm" onclick="location.hash='#/simulado'">
        Ir para o simulado →
      </button>
    </div>
    ${r.questoes.map((q, i) => `
      <div class="qgerada" data-qid="${q.id}">
        <div class="qgerada__num">${String(i + 1).padStart(2, '0')}</div>
        <div class="qgerada__corpo">
          <div class="enunciado" style="border-left:0;padding-left:0;background:transparent;color:var(--txt)">${esc(q.enunciado)}</div>
          <div class="opcoes-simples">
            ${q.alternativas.map((a) => `
              <button class="opcao-simples" data-letra="${a.letra}">
                <span class="bolha bolha--sm">${a.letra}</span>
                <span>${esc(a.texto)}</span>
              </button>`).join('')}
          </div>
          <div class="qgerada__feedback" hidden></div>
        </div>
      </div>`).join('')}
  `;

  $$('.qgerada', alvo).forEach((div) => {
    $$('.opcao-simples', div).forEach((b) =>
      b.addEventListener('click', () => responderGerada(div, b.dataset.letra)));
  });
}

async function responderGerada(div, letra) {
  const qid = +div.dataset.qid;
  if (div.dataset.travada) return;
  div.dataset.travada = '1';
  $$('.opcao-simples', div).forEach((b) => b.disabled = true);

  try {
    const r = await api(`/questoes/${qid}/responder`, {
      method: 'POST',
      body: JSON.stringify({ resposta: letra, segundos: 0 }),
    });
    $$('.opcao-simples', div).forEach((b) => {
      if (b.dataset.letra === r.gabarito) b.classList.add('is-certa');
      else if (b.dataset.letra === r.sua_resposta) b.classList.add('is-errada');
    });

    const fb = $('.qgerada__feedback', div);
    fb.hidden = false;
    fb.innerHTML = `
      <div class="veredito ${r.acertou ? 'veredito--ok' : 'veredito--erro'}">
        <span class="veredito__icone">
          <svg viewBox="0 0 24 24">${r.acertou ? '<path d="M4 12l5 5L20 6"/>' : '<path d="M6 6l12 12M18 6L6 18"/>'}</svg>
        </span>
        <span>${r.acertou ? 'Resposta certa.' : `Gabarito: ${r.gabarito}.`}
          <small>Leia a explicação abaixo antes de seguir.</small></span>
      </div>
      <div class="cartao mt-1"><div class="pensando">
        <span class="pensando__pontos"><i></i><i></i><i></i></span>Carregando explicação…</div></div>`;

    const exp = await api(`/questoes/${qid}/explicacao`);
    $('.cartao', fb).innerHTML = `<h4 class="cartao__titulo">Explicação</h4><div class="md">${md(exp.texto)}</div>`;
  } catch (err) {
    toast(err.message, 'erro');
    div.removeAttribute('data-travada');
    $$('.opcao-simples', div).forEach((b) => b.disabled = false);
  }
}


/* ═══ VIEW: HISTÓRICO ═════════════════════════════════════════════════════ */

async function viewHistorico(app) {
  app.innerHTML = `
    <div class="pagina__topo">
      <span class="olho">Arquivo</span>
      <h1 class="pagina__titulo">Minhas redações</h1>
      <p class="pagina__sub">Todas as correções ficam guardadas na sua conta. Toque em uma
      para reabrir a nota, os comentários e as reescritas.</p>
    </div>
    <div id="lista">${'<div class="esq esq--bloco" style="height:76px;margin-bottom:.7rem"></div>'.repeat(3)}</div>`;

  const reds = await api('/redacoes');

  if (!reds.length) {
    $('#lista').innerHTML = `<div class="vazio">
      <div class="vazio__icone"><svg viewBox="0 0 24 24"><path d="M5 4h11l4 4v12H5zM15 4v5h5"/></svg></div>
      <h3>Seu arquivo ainda está vazio</h3>
      <p>Assim que você corrigir a primeira redação, ela aparece aqui com nota, comentários e reescritas.</p>
      <button class="btn btn--primary" onclick="location.hash='#/redacao'">Corrigir minha primeira redação</button>
    </div>`;
    return;
  }

  $('#lista').innerHTML = reds.map((r) => `
    <div>
      <button class="item" data-id="${r.id}">
        <span class="item__nota" style="color:${corNota(r.nota_final)}">${r.nota_final}</span>
        <span class="item__meio">
          <span class="item__tema">${esc(r.tema)}</span>
          <span class="item__data">
            <span>${dataBR(r.criado_em)}</span>
            <span aria-hidden="true">·</span>
            <b>C1 ${r.c1}</b><b>C2 ${r.c2}</b><b>C3 ${r.c3}</b><b>C4 ${r.c4}</b><b>C5 ${r.c5}</b>
          </span>
        </span>
        <span class="item__seta">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6"/></svg>
        </span>
      </button>
      <div class="detalhe" data-detalhe="${r.id}" hidden style="margin:0 0 1.4rem"></div>
    </div>`).join('');

  $$('.item', app).forEach((b) => b.addEventListener('click', async () => {
    const alvo = $(`[data-detalhe="${b.dataset.id}"]`);
    const abrindo = alvo.hidden;

    $$('[data-detalhe]', app).forEach((d) => { d.hidden = true; d.innerHTML = ''; });
    $$('.item', app).forEach((i) => i.classList.remove('is-aberto'));
    if (!abrindo) return;

    b.classList.add('is-aberto');
    alvo.hidden = false;
    alvo.innerHTML = '<div class="esq esq--bloco" style="height:200px"></div>';
    try {
      const r = await api(`/redacoes/${b.dataset.id}`);
      renderCorrecao(alvo, r);
      alvo.insertAdjacentHTML('beforeend', `
        <details class="cartao mt-2">
          <summary style="cursor:pointer;font-weight:600">Ver o texto que você enviou</summary>
          <p class="cartao__texto mt-2" style="white-space:pre-wrap;line-height:1.8">${esc(r.texto)}</p>
        </details>`);
    } catch (err) {
      alvo.innerHTML = `<p class="cartao__texto">${esc(err.message)}</p>`;
    }
  }));
}


/* ═══ VIEW: DESEMPENHO ════════════════════════════════════════════════════ */

async function viewDesempenho(app) {
  app.innerHTML = `
    <div class="pagina__topo">
      <span class="olho">Relatório</span>
      <h1 class="pagina__titulo">Meu desempenho</h1>
      <p class="pagina__sub">Onde você ganha ponto e onde você perde. Use este relatório
      para escolher o que treinar na próxima semana.</p>
    </div>
    <div id="corpo">${'<div class="esq esq--bloco" style="height:230px;margin-bottom:1.1rem"></div>'.repeat(2)}</div>`;

  const d = await api('/desempenho');
  const maisFraca = [...d.competencias].sort((a, b) => a.media - b.media)[0];
  const semDados = !d.redacoes && !d.questoes;

  if (semDados) {
    $('#corpo').innerHTML = `<div class="vazio">
      <div class="vazio__icone"><svg viewBox="0 0 24 24"><path d="M4 20V10m5 10V4m5 16v-7m5 7V8"/></svg></div>
      <h3>Ainda não há dados para analisar</h3>
      <p>Corrija uma redação ou responda algumas questões e este relatório se monta sozinho.</p>
      <button class="btn btn--primary" onclick="location.hash='#/simulado'">Começar pelo simulado</button>
    </div>`;
    return;
  }

  $('#corpo').innerHTML = `
    <div class="grade grade--4 mb-3">
      <div class="stat"><div class="stat__k" data-conta="${d.melhor_redacao}">0</div><div class="stat__l">Melhor redação</div></div>
      <div class="stat stat--amarelo"><div class="stat__k" data-conta="${d.media_redacao}">0</div><div class="stat__l">Média geral</div></div>
      <div class="stat stat--verde"><div class="stat__k">${d.taxa_acerto}<span style="font-size:1.1rem">%</span></div><div class="stat__l">Acerto em questões</div></div>
      <div class="stat"><div class="stat__k" data-conta="${d.dias_ativos}">0</div><div class="stat__l">Dias de treino</div></div>
    </div>

    ${d.evolucao.length > 1 ? `
      <div class="gcaixa gcaixa__evolucao mb-3">
        <h3 class="gcaixa__titulo">Evolução das notas</h3>
        <p class="gcaixa__sub">Cada ponto é uma redação corrigida, na ordem em que você enviou.</p>
        ${linhaEvolucao(d.evolucao)}
      </div>` : ''}

    <div class="grade grade--2 mb-3">
      <div class="gcaixa">
        <h3 class="gcaixa__titulo">Radar das competências</h3>
        <p class="gcaixa__sub">Média de cada competência, de 0 a 200.</p>
        ${d.redacoes ? radarCompetencias(d.competencias)
          : '<p class="cartao__texto">Corrija uma redação para desenhar o radar.</p>'}
      </div>

      <div class="gcaixa">
        <h3 class="gcaixa__titulo">Aproveitamento por disciplina</h3>
        <p class="gcaixa__sub">Percentual de acerto nas questões que você respondeu.</p>
        ${d.disciplinas.length ? d.disciplinas.map((x) => `
          <div class="barra-disc">
            <div class="barra-disc__topo">
              <span>${esc(x.disciplina)} <span style="color:var(--txt-3)">· ${x.acertos}/${x.total}</span></span>
              <span class="barra-disc__pct" style="color:${corNota(x.pct, 100)}">${x.pct}%</span>
            </div>
            <div class="barra-disc__trilho">
              <div class="barra-disc__fill" data-largura="${x.pct}" style="background:${corNota(x.pct, 100)}"></div>
            </div>
          </div>`).join('')
          : '<p class="cartao__texto">Responda questões para liberar este gráfico.</p>'}
      </div>
    </div>

    ${d.redacoes ? `
      <div class="bloco bloco--info">
        <h4>Onde focar agora</h4>
        <p style="color:var(--txt-2);font-size:.93rem;line-height:1.65">
          Sua competência mais frágil é a <b>C${maisFraca.numero} — ${esc(maisFraca.titulo)}</b>,
          com média de ${maisFraca.media} de 200 pontos.
          ${maisFraca.numero === 5
            ? 'Treine propostas de intervenção completas: agente, ação, meio, finalidade e detalhamento, nessa ordem.'
            : maisFraca.numero === 4
            ? 'Trabalhe conectivos entre parágrafos e dentro deles — é o ajuste que rende ponto mais rápido.'
            : maisFraca.numero === 3
            ? 'Estruture cada parágrafo com tese, argumento e repertório, sempre nessa sequência.'
            : maisFraca.numero === 2
            ? 'Amplie o repertório sociocultural e amarre cada citação ao tema, sem enfeite solto.'
            : 'Revise concordância, regência e pontuação: são os erros que mais derrubam a C1.'}
        </p>
      </div>` : ''}
  `;

  $$('[data-conta]', app).forEach((el) => animarNumero(el, +el.dataset.conta));
  requestAnimationFrame(() => {
    $$('.barra-disc__fill', app).forEach((b, i) =>
      setTimeout(() => { b.style.width = `${b.dataset.largura}%`; }, 80 * i));
  });
}


/* ═══ INICIALIZAÇÃO ═══════════════════════════════════════════════════════ */

async function iniciarApp() {
  const dados = await api('/auth/eu');
  estado.usuario = dados.usuario;
  estado.iaAtiva = dados.ia_ativa;

  $('#auth').hidden = true;
  $('#shell').hidden = false;

  $('#user-nome').textContent = estado.usuario.nome;
  $('#user-email').textContent = estado.usuario.email;
  $('#avatar').textContent = estado.usuario.nome.trim().charAt(0).toUpperCase();

  const chip = $('#chip-ia');
  chip.className = `chip ${estado.iaAtiva ? 'chip--verde' : 'chip--vermelho'}`;
  chip.innerHTML = `<span class="chip__ponto"></span>${estado.iaAtiva ? 'IA ativa' : 'IA off'}`;

  if (!location.hash) location.hash = '#/inicio';
  await rotear();
}

async function iniciar() {
  montarTabsAuth();
  ligarFormularios();
  ligarNavegacao();

  if (estado.token) {
    try {
      await iniciarApp();
      return;
    } catch {
      localStorage.removeItem('nm_token');
      estado.token = null;
    }
  }
  $('#auth').hidden = false;
}

iniciar();
