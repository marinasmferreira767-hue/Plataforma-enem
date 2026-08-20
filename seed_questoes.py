"""Banco inicial de questões, para a plataforma já funcionar antes de importar PDFs."""

from db import agora, conectar

DEMO = [
    ("Matemática", "Uma loja vende um produto por R$ 240,00. Durante a liquidação, o preço recebeu "
     "um desconto de 15% e, na semana seguinte, um novo desconto de 20% sobre o valor já reduzido. "
     "Qual é o preço final do produto?",
     "R$ 144,00", "R$ 156,00", "R$ 163,20", "R$ 168,00", "R$ 180,00", "C"),
    ("Matemática", "Um reservatório cilíndrico tem 2 m de raio da base e 5 m de altura. "
     "Considerando π ≈ 3, qual é a capacidade aproximada desse reservatório, em litros?",
     "6 000 L", "30 000 L", "60 000 L", "150 000 L", "300 000 L", "C"),
    ("Matemática", "A média das notas de 9 alunos é 6,0. Ao incluir a nota de um décimo aluno, "
     "a média sobe para 6,3. Qual foi a nota desse décimo aluno?",
     "6,3", "7,5", "8,0", "9,0", "10,0", "D"),
    ("Matemática", "Em uma progressão aritmética, o primeiro termo é 7 e a razão é 4. "
     "Qual é o vigésimo termo dessa sequência?",
     "76", "80", "83", "87", "91", "C"),
    ("Ciências da Natureza", "O efeito estufa é um fenômeno natural essencial para a manutenção da "
     "temperatura na Terra. Sua intensificação recente está associada principalmente ao aumento da "
     "concentração atmosférica de qual gás resultante da queima de combustíveis fósseis?",
     "Gás nitrogênio (N₂)", "Gás oxigênio (O₂)", "Dióxido de carbono (CO₂)",
     "Gás hélio (He)", "Gás argônio (Ar)", "C"),
    ("Ciências da Natureza", "Um corpo de 4 kg parte do repouso e atinge 12 m/s em 6 segundos sob "
     "aceleração constante. Qual é a intensidade da força resultante sobre ele?",
     "2 N", "4 N", "8 N", "12 N", "48 N", "C"),
    ("Ciências da Natureza", "Nas células eucarióticas, a organela responsável pela respiração "
     "celular, processo que produz a maior parte do ATP utilizado pela célula, é:",
     "O ribossomo", "A mitocôndria", "O lisossomo",
     "O complexo golgiense", "O retículo endoplasmático rugoso", "B"),
    ("Ciências da Natureza", "A chuva ácida é um problema ambiental associado à emissão industrial "
     "de óxidos que reagem com a água atmosférica. Os principais responsáveis por esse fenômeno são:",
     "Óxidos de enxofre e de nitrogênio", "Óxidos de sódio e de potássio",
     "Óxidos de cálcio e de magnésio", "Óxidos de ferro e de alumínio",
     "Óxidos de hélio e de argônio", "A"),
    ("Ciências Humanas", "A Lei Áurea, assinada em 1888, aboliu formalmente a escravidão no Brasil. "
     "Contudo, a ausência de políticas de inclusão da população negra recém-libertada resultou "
     "principalmente em:",
     "Distribuição ampla de terras aos ex-escravizados",
     "Acesso imediato à educação pública de qualidade",
     "Marginalização social e econômica prolongada dessa população",
     "Substituição do trabalho livre pelo trabalho compulsório indígena",
     "Concessão automática de direitos políticos plenos", "C"),
    ("Ciências Humanas", "A urbanização acelerada das metrópoles brasileiras a partir da segunda "
     "metade do século XX produziu a periferização da moradia. Esse processo é explicado sobretudo pela:",
     "Redução do preço da terra nas áreas centrais",
     "Especulação imobiliária, que empurra a população de baixa renda para áreas distantes",
     "Diminuição da migração campo-cidade no período",
     "Política habitacional que priorizou o centro para famílias de baixa renda",
     "Queda contínua da população urbana em relação à rural", "B"),
    ("Ciências Humanas", "A Revolução Industrial iniciada na Inglaterra no século XVIII transformou "
     "as relações de trabalho ao:",
     "Fortalecer as corporações de ofício medievais",
     "Substituir a manufatura artesanal pela produção fabril assalariada",
     "Eliminar a divisão do trabalho nas fábricas",
     "Reduzir a jornada de trabalho já em suas primeiras décadas",
     "Impedir a migração de trabalhadores rurais para as cidades", "B"),
    ("Ciências Humanas", "A Constituição de 1988 ficou conhecida como Constituição Cidadã "
     "principalmente por:",
     "Restringir a participação popular nas decisões políticas",
     "Ampliar direitos sociais e garantias fundamentais aos cidadãos",
     "Concentrar poderes no Executivo federal",
     "Eliminar a autonomia dos estados e municípios",
     "Suspender o direito de voto dos analfabetos", "B"),
    ("Linguagens", "Na frase 'Fazem cinco anos que ele não visita a cidade', a norma-padrão "
     "recomenda a correção do verbo porque:",
     "O verbo 'fazer' indicando tempo decorrido é impessoal e fica no singular",
     "O sujeito da oração é 'cinco anos', exigindo plural",
     "O verbo deveria estar no futuro do pretérito",
     "'Fazer' nunca admite flexão de número em português",
     "A oração exige voz passiva sintética", "A"),
    ("Linguagens", "A função da linguagem predominante em uma campanha publicitária que usa verbos "
     "no imperativo para levar o público a comprar um produto é a função:",
     "Referencial", "Emotiva", "Fática", "Conativa", "Metalinguística", "D"),
    ("Linguagens", "O Modernismo brasileiro de 1922 caracterizou-se, entre outros aspectos, por:",
     "Retomar o rigor formal do Parnasianismo",
     "Valorizar a linguagem coloquial e a identidade cultural brasileira",
     "Rejeitar qualquer influência das vanguardas europeias",
     "Defender o uso exclusivo da métrica clássica",
     "Restringir a produção literária à poesia religiosa", "B"),
    ("Linguagens", "Em 'O menino, que estudava muito, passou no vestibular', a oração entre "
     "vírgulas classifica-se como subordinada adjetiva:",
     "Restritiva", "Explicativa", "Consecutiva", "Concessiva", "Final", "B"),
]


def semear() -> int:
    with conectar() as c:
        if c.execute("SELECT COUNT(*) FROM questoes").fetchone()[0] > 0:
            return 0
        for i, (disc, en, a, b, cc, d, e, gab) in enumerate(DEMO, start=1):
            c.execute(
                """INSERT OR IGNORE INTO questoes
                   (fonte,numero,ano,prova,disciplina,enunciado,
                    alt_a,alt_b,alt_c,alt_d,alt_e,gabarito,criado_em)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("banco_inicial", i, 2024, "Banco inicial", disc, en,
                 a, b, cc, d, e, gab, agora()),
            )
    return len(DEMO)
