from flask import Flask, render_template_string, request, redirect, session, url_for, abort
import calendar
import os
import secrets
import sqlite3
from datetime import datetime
 
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash
 
app = Flask(__name__)
# Defina SECRET_KEY no ambiente em produção. Sem isso, uma chave aleatória é gerada
# a cada inicialização (as sessões expiram quando o servidor reinicia).
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
 
SENHA_ADMIN_INICIAL = os.environ.get("ADMIN_SENHA", "1234")
 
 
def esc(valor):
    """Escapa HTML e também chaves {}, para que texto digitado por usuários
    nunca seja interpretado pelo Jinja dentro de render_template_string."""
    return str(escape(valor if valor is not None else "")).replace("{", "&#123;").replace("}", "&#125;")
 
 
def conectar():
    return sqlite3.connect("banco.db")
 
 
def inicializar_banco():
    """Cria as tabelas (usuarios, avisos), garante colunas novas e o usuário admin."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            turma TEXT,
            tipo TEXT DEFAULT 'aluno'
        )
    """)
 
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas_existentes = [linha[1] for linha in cursor.fetchall()]
    if "turma" not in colunas_existentes:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN turma TEXT")
    if "tipo" not in colunas_existentes:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN tipo TEXT DEFAULT 'aluno'")
 
    # turma NULL = aviso para todas as turmas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS avisos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turma TEXT,
            texto TEXT NOT NULL,
            autor TEXT NOT NULL,
            criado_em TEXT NOT NULL
        )
    """)
 
    cursor.execute("SELECT usuario FROM usuarios WHERE usuario = ?", ("admin",))
    if not cursor.fetchone():
        senha_hash = generate_password_hash(SENHA_ADMIN_INICIAL)
        cursor.execute(
            "INSERT INTO usuarios (usuario, senha, turma, tipo) VALUES (?, ?, ?, ?)",
            ("admin", senha_hash, None, "admin")
        )
    else:
        cursor.execute("UPDATE usuarios SET tipo = 'admin' WHERE usuario = 'admin'")
 
    conn.commit()
    conn.close()
 
 
# --- CSRF ---
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]
 
 
def csrf_input():
    return f'<input type="hidden" name="csrf" value="{csrf_token()}">'
 
 
@app.before_request
def verificar_csrf():
    if request.method == "POST":
        token = request.form.get("csrf")
        if not token or token != session.get("csrf"):
            abort(400, "Token de segurança inválido. Volte e tente novamente.")
 
 
# --- CONFIGURAÇÕES FIXAS 2026 ---
ANO_FIXO = 2026
MESES_NOME = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
DIAS_SEMANA_PY = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
 
eventos_fixos = {
    1: {1: "Férias coletivas", 6: "Matrícula presencial", 26: "Semana formativa"},
    2: {2: "Formação tecnológica", 9: "Planejamento", 16: "Feriado", 17: "Feriado", 18: "Feriado", 19: "Início das aulas"},
    3: {2: "Avaliação diagnóstica", 14: "Reposição de aulas", 16: "1º Miniteste", 26: "NM1 (1º Tri)"},
    4: {2: "Feriado", 3: "Feriado", 13: "2º Miniteste", 18: "Reposição", 21: "Feriado", 23: "1º Simulado"},
    5: {1: "Feriado", 11: "3º Miniteste", 16: "Reposição", 18: "Simulado ENEM+", 22: "NM3 (1º Tri)", 25: "Início 2º Tri"},
    6: {1: "Conselho Classe", 4: "Feriado", 8: "4º Miniteste", 19: "NM1 (2º Tri)", 20: "Reposição"},
    7: {10: "2º Simulado", 11: "Fim 1º Semestre", 13: "Férias coletivas", 28: "Planejamento", 30: "Início 2º Semestre"},
    8: {10: "5º Miniteste", 15: "Sábado Letivo", 22: "Reposição", 31: "2º Simulado ENEM+"},
    9: {4: "NM3 (2º Tri)", 7: "Feriado", 8: "Início 3º Tri", 14: "6º Miniteste / Conselho", 19: "Reposição"},
    10: {2: "NM1 (3º Tri)", 5: "7º Miniteste", 12: "Feriado", 15: "Feriado", 19: "Feriado", 24: "Reposição", 26: "3º Simulado ENEM+", 30: "Feriado"},
    11: {1: "ENEM 2026", 2: "Feriado", 6: "NM2 (3º Tri)", 14: "Reposição", 16: "8º Miniteste", 20: "Feriado"},
    12: {4: "3º Simulado", 11: "NM3 (3º Tri)", 14: "Recuperação Paralela", 16: "Término Ano Letivo", 18: "Recuperação Final", 21: "Provas Finais", 23: "Férias"}
}
eventos_privados = {}
 
horarios_escolares = {
    "1A": {
        "Segunda": ["Física (Paulo)", "Física (Paulo)", "Zootecnia (Erika)", "Zootecnia (Erika)", "Espanhol (Gilmara)", "Artes (Gilmara)", "Olericultura (Erika)", "Olericultura (Erika)"],
        "Terça": ["Agroecologia (Erika)", "Agroecologia (Erika)", "Geoprocessamento (Erika)", "Geoprocessamento (Erika)", "Matemática (Joaquim)", "Matemática (Joaquim)", "Forragicultura (Erika)", "Forragicultura (Erika)"],
        "Quarta": ["Geografia (Vânia)", "Geografia (Vânia)", "Ed. Física (Thais)", "Esportes (Thais)", "Sociologia (Vânia)", "Int. Artes (Emerson)", "História (Denis)", "História (Denis)"],
        "Quinta": ["Português (Sorley)", "Português (Sorley)", "Biologia (Emerson)", "Biologia (Emerson)", "Filosofia (Denis)", "Projeto de Vida (M. Noelia)", "Matemática/Rec (Joaquim)", "Olimpíada (Paulo)"],
        "Sexta": ["Leitura/Produção (Sorley)", "Português/Recom (Sorley)", "Química (Marcos)", "Química (Marcos)", "Matemática (Joaquim)", "Ed. Financeira (Joaquim)", "Inglês (M. Noelia)", "Inglês (M. Noelia)"]
    },
    "1B": {
        "Segunda": ["Geografia (Vânia)", "Geografia (Vânia)", "Física (Paulo)", "Física (Paulo)", "Matemática/Rec (Euclides)", "Forragicultura (Wemerson)", "Espanhol (Gilmara)", "Artes (Gilmara)"],
        "Terça": ["Int. Artes (Julio)", "Clube de Leitura (Janylle)", "Biologia (Emerson)", "Biologia (Emerson)", "Ed. Física (Thais)", "Esportes (Thais)", "Matemática (Joaquim)", "Matemática (Joaquim)"],
        "Quarta": ["Geoprocessamento (Wemerson)", "Geoprocessamento (Wemerson)", "História (Denis)", "História (Denis)", "Filosofia (Denis)", "Sociologia (Vânia)", "Matemática (Joaquim)", "Ed. Financeira (Joaquim)"],
        "Quinta": ["Agroecologia (Wemerson)", "Agroecologia (Wemerson)", "Forragicultura (Wemerson)", "Projeto de Vida (M. Noelia)", "Leitura/Produção (Sorley)", "Português/Recom (Sorley)", "Zootecnia (Wemerson)", "Zootecnia (Wemerson)"],
        "Sexta": ["Inglês (M. Noelia)", "Inglês (M. Noelia)", "Olericultura (Wemerson)", "Olericultura (Wemerson)", "Português (Sorley)", "Português (Sorley)", "Química (Marcos)", "Química (Marcos)"]
    },
    "2B": {
        "Segunda": ["Desenvolvimento de Sistemas (Wemerson)", "Desenvolvimento de Sistemas (Wemerson)", "Desenvolvimento de Sistemas (Wemerson)", "Desenvolvimento de Sistemas (Wemerson)", "Desenvolvimento de Sistemas (Wemerson)", "Matemática/Rec (Euclides)", "Geografia (Vânia)", "Sociologia (Vânia)"],
        "Terça": ["Desenvolvimento de Sistemas (Wemerson)", "Espanhol (Gilmara)", "Ed. Física (Thais)", "Esportes (Thais)", "Biologia (Emerson)", "Biologia (Emerson)", "Clube de Leitura (Janylle)", "Artes (Janylle)"],
        "Quarta": ["Filosofia (Denis)", "Int. Artes (Emerson)", "Desenvolvimento de Sistemas (Wemerson)", "Desenvolvimento de Sistemas (Wemerson)", "Química (Marcos)", "Química (Marcos)", "Português (Vanessa)", "Português (Vanessa)"],
        "Quinta": ["Física (Paulo)", "Física (Paulo)", "Português/Recom (Sorley)", "Português/Recom (Sorley)", "Matemática (Joaquim)", "História (Denis)", "Inglês (M. Noelia)", "Inglês Aprof. (M. Noelia)"],
        "Sexta": ["Desenvolvimento de Sistemas (Wemerson)", "Desenvolvimento de Sistemas (Wemerson)", "Projeto de Vida (Sorley)", "Matemática (H. Estudo) (Joaquim)", "Matemática/Rec (Euclides)", "Leitura/Produção (Vanessa)", "Matemática (Joaquim)", "Ed. Financeira (Joaquim)"]
    },
    "3A": {
        "Segunda": ["Matemática (Euclides)", "Matemática (Euclides)", "Ed. Trânsito (Emerson)", "Ed. Trânsito (Emerson)", "Física (Paulo)", "Física (Paulo)", "Matemática (Euclides)", "Matemática/Rec (Euclides)"],
        "Terça": ["Ed. Trânsito (Emerson)", "Ed. Trânsito (Emerson)", "Inglês (Janylle)", "Inglês (Janylle)", "Biologia (Erika)", "Cultura/Artes (Janylle)", "Ed. Física (Thais)", "Esportes (Thais)"],
        "Quarta": ["Int. Artes (Emerson)", "Filosofia (Denis)", "Geografia (Vânia)", "Sociologia (Vânia)", "Português (Vanessa)", "Português (Vanessa)", "Química (Marcos)", "Química (Marcos)"],
        "Quinta": ["Desenvolvimento de Sistemas (Josean)", "Desenvolvimento de Sistemas (Josean)", "Desenvolvimento de Sistemas (Josean)", "Desenvolvimento de Sistemas (Josean)", "Português/Recom (Vanessa)", "Português/Recom (Vanessa)", "Projeto Aprof. C. Natureza (Paulo)", "História (Denis)"],
        "Sexta": ["Desenvolvimento de Sistemas (Josean)", "Desenvolvimento de Sistemas (Josean)", "Desenvolvimento de Sistemas (Josean)", "Matemática (H. Estudo) (Euclides)", "Português (Vanessa)", "Desenvolvimento de Sistemas (Josean)", "Desenvolvimento de Sistemas (Josean)", "Desenvolvimento de Sistemas (Josean)"]
    },
    "3B": {
        "Segunda": ["Espanhol (Gilmara)", "Artes (Gilmara)", "Matemática (Euclides)", "Matemática (Euclides)", "Ed. Física (Thais)", "Esportes (Thais)", "Física (Paulo)", "Física (Paulo)"],
        "Terça": ["Cultura/Artes (Janylle)", "Desenvolvimento de Sistemas (Julio)", "Desenvolvimento de Sistemas (Julio)", "Desenvolvimento de Sistemas (Julio)", "Desenvolvimento de Sistemas (Julio)", "Biologia (Erika)", "Ed. Trânsito (Emerson)", "Ed. Trânsito (Emerson)"],
        "Quarta": ["Desenvolvimento de Sistemas (Julio)", "Desenvolvimento de Sistemas (Julio)", "Desenvolvimento de Sistemas (Julio)", "Desenvolvimento de Sistemas (Julio)", "Int. Artes (Julio)", "História (Denis)", "Geografia (Vânia)", "Geografia (Vânia)"],
        "Quinta": ["Desenvolvimento de Sistemas (Julio)", "Desenvolvimento de Sistemas (Julio)", "Português (Vanessa)", "Português (Vanessa)", "Inglês (M. Noelia)", "Projeto Aprof. C. Natureza (Paulo)", "Filosofia (Denis)", "Português (Vanessa)"],
        "Sexta": ["Matemática (Euclides)", "Matemática Recomp. (Euclides)", "Matemática (H. Estudo) (Euclides)", "Inglês (M. Noelia)", "Química (Marcos)", "Química (Marcos)", "Português/Recom (Vanessa)", "Português/Recom (Vanessa)"]
    }
}
 
TURMAS_DISPONIVEIS = list(horarios_escolares.keys())
 
 
def obter_materiais_hoje(turma):
    """Retorna (dia_semana, lista_de_materias) da grade da turma para hoje."""
    hoje = datetime.now()
    dia_semana = DIAS_SEMANA_PY[hoje.weekday()]
    grade_turma = horarios_escolares.get(turma, {})
    aulas_hoje = grade_turma.get(dia_semana, [])
 
    materias = []
    for aula in aulas_hoje:
        materia = aula.split(" (")[0].strip()
        if materia and materia not in materias:
            materias.append(materia)
    return dia_semana, materias
 
 
def obter_provas_proximas(dias_limite=10):
    """Varre o calendário 2026 procurando avaliações nos próximos `dias_limite` dias."""
    palavras_chave = ["NM", "Simulado", "Miniteste", "Recuperação", "Prova", "ENEM"]
    hoje = datetime.now()
    resultados = []
 
    for mes, dias in eventos_fixos.items():
        for dia, texto in dias.items():
            if any(p.lower() in texto.lower() for p in palavras_chave):
                try:
                    data_evento = datetime(2026, mes, dia)
                except ValueError:
                    continue
                delta = (data_evento - hoje).days
                if 0 <= delta <= dias_limite:
                    resultados.append((delta, mes, dia, texto))
 
    resultados.sort(key=lambda x: x[0])
    return resultados
 
 
def obter_avisos(turma, eh_admin=False, limite=8):
    """Avisos que o usuário deve ver: os da sua turma + os gerais (turma NULL).
    Admin vê todos."""
    conn = conectar()
    cursor = conn.cursor()
    if eh_admin:
        cursor.execute(
            "SELECT id, turma, texto, autor, criado_em FROM avisos ORDER BY id DESC LIMIT ?",
            (limite,)
        )
    elif turma:
        cursor.execute(
            "SELECT id, turma, texto, autor, criado_em FROM avisos "
            "WHERE turma IS NULL OR turma = ? ORDER BY id DESC LIMIT ?",
            (turma, limite)
        )
    else:
        cursor.execute(
            "SELECT id, turma, texto, autor, criado_em FROM avisos "
            "WHERE turma IS NULL ORDER BY id DESC LIMIT ?",
            (limite,)
        )
    linhas = cursor.fetchall()
    conn.close()
    return linhas
 
 
def gerar_navbar(exibir_voltar=False):
    user = esc(session.get("usuario_logado", "Usuário"))
    turma = session.get("turma")
    tipo = session.get("tipo")
    seta = '<a href="/" class="text-white me-3" style="text-decoration:none;">&#8592; Início</a>' if exibir_voltar else ""
    admin_link = '<a href="/admin" class="btn btn-warning btn-sm me-2">⚙️ Admin</a>' if tipo == "admin" else ""
    label_usuario = f"{user} ({esc(turma)})" if turma else user
    return f"""
    <nav class="navbar navbar-dark shadow-sm" style="background:#155888; padding: 10px 12px;">
      <div class="container-fluid flex-wrap gap-2">
        <div class="d-flex align-items-center flex-wrap">{seta}<span class="navbar-brand mb-0" style="font-size: 1.1rem;">🎓 Sistema Escolar 2026</span></div>
        <div class="text-white small font-monospace d-flex align-items-center flex-wrap gap-2 ms-auto">{admin_link}<span>{label_usuario}</span> <a href="/logout" class="btn btn-danger btn-sm">Sair</a></div>
      </div>
    </nav>"""
 
 
@app.route("/")
def home():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
 
    hoje = datetime.now()
    mes_atual = hoje.month
    dia_atual = hoje.day
 
    # --- LÓGICA INTELIGENTE DE EVENTOS ---
    evento_exibir = eventos_fixos.get(mes_atual, {}).get(dia_atual)
 
    if not evento_exibir:
        eventos_mes = eventos_fixos.get(mes_atual, {})
        proximos_dias = sorted([d for d in eventos_mes.keys() if d > dia_atual])
        if proximos_dias:
            dia_prox = proximos_dias[0]
            evento_exibir = f"Próximo: Dia {dia_prox:02d} - {eventos_mes[dia_prox]}"
        else:
            evento_exibir = "Consulte o calendário para os eventos de 2026."
 
    # --- MURAL: LIVROS DO DIA E PROVAS PRÓXIMAS ---
    turma_usuario = session.get("turma")
    if turma_usuario:
        dia_semana_label, livros_hoje = obter_materiais_hoje(turma_usuario)
        if livros_hoje:
            livros_html = "<ul class='mb-0 small ps-3'>" + "".join([f"<li>{esc(m)}</li>" for m in livros_hoje]) + "</ul>"
        else:
            livros_html = "<p class='small text-muted mb-0'>Sem aulas registradas para hoje.</p>"
    else:
        dia_semana_label = DIAS_SEMANA_PY[hoje.weekday()]
        livros_html = "<p class='small text-muted mb-0'>Defina sua turma (fale com a secretaria ou peça pro admin) para ver os livros do dia.</p>"
 
    provas_proximas = obter_provas_proximas()
    if provas_proximas:
        itens = []
        for delta, mes, dia, texto in provas_proximas[:4]:
            if delta == 0:
                prazo = "Hoje!"
            elif delta == 1:
                prazo = "Amanhã"
            else:
                prazo = f"em {delta} dias"
            itens.append(f"<li><b>{esc(texto)}</b> — {dia:02d}/{mes:02d} ({prazo})</li>")
        provas_html = "<ul class='mb-0 small ps-3'>" + "".join(itens) + "</ul>"
    else:
        provas_html = "<p class='small text-muted mb-0'>Nenhuma prova ou avaliação nos próximos 10 dias.</p>"
 
    # --- AVISOS DA TURMA (cadastrados pelo admin) ---
    eh_admin = session.get("tipo") == "admin"
    avisos = obter_avisos(turma_usuario, eh_admin)
    if avisos:
        itens_avisos = []
        for _id, turma_aviso, texto, autor, criado_em in avisos:
            if turma_aviso:
                selo = f'<span class="badge bg-primary me-1">Turma {esc(turma_aviso)}</span>'
            else:
                selo = '<span class="badge bg-secondary me-1">Todas as turmas</span>'
            itens_avisos.append(
                f'<li class="mb-3">📣 {selo}<span style="white-space:pre-line">{esc(texto)}</span>'
                f'<div class="text-muted" style="font-size:0.75rem;">{esc(autor)} · {esc(criado_em)}</div></li>'
            )
        avisos_html = '<ul class="list-unstyled mb-0">' + "".join(itens_avisos) + "</ul>"
    else:
        avisos_html = '<p class="small text-muted mb-0">Nenhum aviso para a sua turma no momento.</p>'
 
    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .card-dash {{ border: none; border-radius: 15px; transition: 0.3s; background: white; text-decoration: none !important; color: inherit; }}
            .card-dash:hover {{ transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }}
            .welcome-section {{ background: linear-gradient(45deg, #155888, #2a94d6); color: white; padding: 40px; border-radius: 15px; }}
            .event-card {{ background: #0a2e47; color: #ffca28; border-left: 5px solid #ffca28; min-height: 200px; }}
            .btn-action {{ border-radius: 12px; padding: 20px; }}
            @media (max-width: 767px) {{
                .welcome-section {{ padding: 24px 16px; }}
                .welcome-section h1 {{ font-size: 1.6rem; }}
                .welcome-section .lead {{ font-size: 0.95rem; }}
                .event-card {{ min-height: auto; padding: 20px !important; }}
                .btn-action {{ padding: 14px; }}
                .btn-action .display-4 {{ font-size: 2rem; }}
                .container {{ padding-left: 12px; padding-right: 12px; }}
            }}
        </style>
    </head>
    <body class="bg-light">{gerar_navbar()}
    <div class="container mt-4">
        <div class="welcome-section shadow mb-4 text-center">
            <h1 class="fw-bold">CETI Job de Macedo Brito 🏫</h1>
            <p class="lead">Portal Acadêmico Oficial - Ano Letivo {ANO_FIXO}</p>
        </div>
 
        <div class="row">
            <div class="col-md-8">
                <div class="card card-dash shadow-sm p-4 mb-4">
                    <h4 style="color:#155888">🏛️ Mural de Avisos</h4>
                    <hr>
                    <div class="mb-3">{avisos_html}</div>
                    <hr>
                    <ul class="list-unstyled mb-0">
                        <li class="mb-3">✅ <b>Tempo Integral:</b> Horário de 8 aulas (Manhã e Tarde).</li>
                        <li class="mb-3">📌 <b>Início das Aulas:</b> Confirmado para 19/02/2026.</li>
                        <li class="mb-0">⚠️ <b>Documentação:</b> Verifique sua matrícula na secretaria.</li>
                    </ul>
                </div>
 
                <div class="row mb-4">
                    <div class="col-md-6 mb-3 mb-md-0">
                        <div class="card card-dash shadow-sm p-3 h-100" style="border-left: 5px solid #155888;">
                            <h6 class="fw-bold" style="color:#155888">📚 Livros para hoje ({dia_semana_label})</h6>
                            <hr class="my-2">
                            {livros_html}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card card-dash shadow-sm p-3 h-100" style="border-left: 5px solid #dc3545;">
                            <h6 class="fw-bold text-danger">📝 Provas se aproximando</h6>
                            <hr class="my-2">
                            {provas_html}
                        </div>
                    </div>
                </div>
 
                <div class="row text-center">
                    <div class="col-md-6 mb-3">
                        <a href="/turmas" class="card card-dash shadow-sm btn-action h-100">
                            <div class="display-4 mb-2">📚</div>
                            <h5 class="fw-bold">Horários de Aula</h5>
                            <small class="text-muted">Grade completa da semana</small>
                        </a>
                    </div>
                    <div class="col-md-6 mb-3">
                        <a href="/calendario/2026/{mes_atual}" class="card card-dash shadow-sm btn-action h-100">
                            <div class="display-4 mb-2">📅</div>
                            <h5 class="fw-bold">Calendário 2026</h5>
                            <small class="text-muted">Feriados e Datas Letivas</small>
                        </a>
                    </div>
                </div>
            </div>
 
            <div class="col-md-4">
                <div class="card card-dash shadow-sm p-4 event-card d-flex flex-column justify-content-center text-center">
                    <h5 class="fw-bold mb-3">🔔 EVENTO PRÓXIMO</h5>
                    <hr style="border-color: #ffca28; width: 50%; margin: 10px auto;">
                    <p class="fs-5 fw-bold mb-0">{esc(evento_exibir)}</p>
                    <div class="mt-4">
                        <small class="opacity-75">Prepare seu cronograma!</small>
                    </div>
                </div>
 
                <div class="card card-dash shadow-sm p-3 mt-3 text-center border-0" style="background: #e3f2fd;">
                    <p class="mb-0 small text-primary fw-bold">Dica: Use o tempo de intervalo para descansar a mente!</p>
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>""")
 
 
# ------------------- CALENDÁRIO -------------------
@app.route("/calendario")
@app.route("/calendario/<int:ano>/<int:mes>")
def ver_calendario(ano=None, mes=None):
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
 
    hoje = datetime.now()
    ano = ano if ano else hoje.year
    mes = mes if mes else hoje.month
 
    if ano != 2026 or not 1 <= mes <= 12:
        return redirect("/calendario/2026/1")  # Trava o ano
 
    prev_mes = mes - 1 if mes > 1 else 12
    next_mes = mes + 1 if mes < 12 else 1
 
    cal = calendar.monthcalendar(2026, mes)
    tabela_html = ""
    user = session["usuario_logado"]
 
    for semana in cal:
        linha = "<tr>"
        for i, dia in enumerate(semana):
            if dia == 0:
                linha += "<td></td>"
            else:
                info_fixo = eventos_fixos.get(mes, {}).get(dia, "")
                info_privado = eventos_privados.get(user, {}).get(mes, {}).get(dia, "")
 
                if info_privado:
                    css = "evento-privado"
                    texto = (
                        f"<div class='evento-texto'>{esc(info_privado)} "
                        f"<form method='POST' action='/excluir_evento/{mes}/{dia}' style='display:inline;' onclick='event.stopPropagation()'>"
                        f"{csrf_input()}<button class='btn btn-link p-0' style='color:red; font-size:0.7rem;'>[X]</button></form></div>"
                    )
                elif info_fixo:
                    css = "evento"
                    texto = f"<div class='evento-texto'>{esc(info_fixo)}</div>"
                else:
                    css = "domingo" if i == 6 else ""
                    texto = ""
 
                if dia == hoje.day and mes == hoje.month:
                    css += " hoje"
 
                linha += f"<td class='{css}' onclick=\"window.location='/add_evento/{mes}/{dia}'\" style='cursor:pointer;'><b>{dia}</b>{texto}</td>"
        tabela_html += linha + "</tr>"
 
    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .calendario-container {{ background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            th {{ background: #155888 !important; color: white !important; }}
            td {{ height: 100px; vertical-align: top; border: 1px solid #eee !important; width: 14%; }}
            .domingo {{ background: #fff5f5; color: #dc3545; }}
            .evento {{ background: #fdf2e9 !important; border-left: 4px solid #155888 !important; }}
            .evento-privado {{ background: #d1f7c4 !important; border-left: 4px solid #28a745 !important; }}
            .evento-texto {{ font-size: 0.7rem; color: #155888; font-weight: bold; margin-top: 5px; }}
            .hoje {{ border: 2px solid #ff9800 !important; border-radius: 50%; }}
            @media (max-width: 767px) {{
                .calendario-container {{ padding: 10px; border-radius: 10px; }}
                .container {{ padding-left: 8px; padding-right: 8px; }}
                table {{ min-width: 650px; }}
                td {{ height: 70px; width: 14%; font-size: 0.75rem; padding: 3px !important; }}
                th {{ font-size: 0.75rem; padding: 4px !important; }}
                .evento-texto {{ font-size: 0.6rem; }}
                h2 {{ font-size: 1.1rem; }}
            }}
        </style>
    </head>
    <body class="bg-light">{gerar_navbar(True)}
        <div class="container mt-4">
            <div class="calendario-container">
                <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                    <a href="/calendario/2026/{prev_mes}" class="btn btn-outline-primary">❮</a>
                    <h2 style="color:#155888" class="text-center flex-grow-1">CALENDÁRIO ESCOLAR {MESES_NOME[mes-1]} 2026</h2>
                    <a href="/calendario/2026/{next_mes}" class="btn btn-outline-primary">❯</a>
                </div>
                <div class="table-responsive">
                    <table class="table table-bordered">
                        <thead><tr><th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th><th>Dom</th></tr></thead>
                        <tbody>{tabela_html}</tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)
 
 
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    erro = ""
 
    if request.method == "POST":
        usuario = (request.form.get("usuario") or "").strip()
        senha = request.form.get("senha") or ""
        confirmar = request.form.get("confirmar") or ""
        turma = request.form.get("turma") or None
        if turma not in TURMAS_DISPONIVEIS:
            turma = None
 
        if not usuario:
            erro = "Informe um nome de usuário."
        elif senha != confirmar:
            erro = "As senhas não coincidem!"
        else:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute("SELECT usuario FROM usuarios WHERE usuario = ?", (usuario,))
 
            if cursor.fetchone():
                conn.close()
                erro = "Usuário já existe!"
            else:
                senha_hash = generate_password_hash(senha)
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha, turma, tipo) VALUES (?, ?, ?, ?)",
                    (usuario, senha_hash, turma, "aluno")
                )
                conn.commit()
                conn.close()
                return redirect("/login")
 
    opcoes_turma = "".join([f'<option value="{t}">{t}</option>' for t in TURMAS_DISPONIVEIS])
    alerta = f'<div class="alert alert-danger py-2">{esc(erro)}</div>' if erro else ""
 
    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <div class="card shadow p-4 col-12 col-md-4 mx-auto">
                <h3 class="text-center mb-4">Criar Conta</h3>
                {alerta}
                <form method="POST">
                    {csrf_input()}
                    <div class="mb-3">
                        <label>Usuário</label>
                        <input type="text" name="usuario" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Turma</label>
                        <select name="turma" class="form-select">
                            <option value="">-- Selecione (opcional) --</option>
                            {opcoes_turma}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label>Senha</label>
                        <input type="password" name="senha" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Confirmar Senha</label>
                        <input type="password" name="confirmar" class="form-control" required>
                    </div>
                    <button class="btn btn-success w-100">Cadastrar</button>
                </form>
                <div class="text-center mt-3">
                    <a href="/login">Já tenho conta</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)
 
 
# ------------------- ADICIONAR EVENTO -------------------
@app.route("/add_evento/<int:mes>/<int:dia>", methods=["GET", "POST"])
def add_evento(mes, dia):
    if "usuario_logado" not in session:
        return redirect("/login")
 
    if request.method == "POST":
        texto = (request.form.get("evento") or "").strip()
        user = session["usuario_logado"]
 
        if texto:
            eventos_privados.setdefault(user, {}).setdefault(mes, {})[dia] = texto
 
        return redirect(f"/calendario/2026/{mes}")
 
    return render_template_string(f"""
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <body class="bg-light">
    <div class="container mt-5 col-12 col-md-4">
        <div class="card p-4 shadow">
            <h4>Adicionar Evento - {dia}/{mes}/2026</h4>
            <form method="POST">
                {csrf_input()}
                <input name="evento" class="form-control mb-3" required>
                <button class="btn btn-success w-100">Salvar</button>
            </form>
        </div>
    </div>
    </body>
    """)
 
 
# ------------------- EXCLUIR EVENTO PRIVADO -------------------
@app.route("/excluir_evento/<int:mes>/<int:dia>", methods=["POST"])
def excluir_evento(mes, dia):
    if "usuario_logado" not in session:
        return redirect("/login")
 
    user = session["usuario_logado"]
    if user in eventos_privados:
        user_eventos = eventos_privados[user]
        if mes in user_eventos:
            if dia in user_eventos[mes]:
                del user_eventos[mes][dia]
                if not user_eventos[mes]:
                    del user_eventos[mes]
            if not user_eventos:
                del eventos_privados[user]
 
    return redirect(f"/calendario/2026/{mes}")
 
 
@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
 
    if request.method == "POST":
        user = request.form.get("usuario")
        senha = request.form.get("senha") or ""
 
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT usuario, senha, turma, tipo FROM usuarios WHERE usuario = ?",
            (user,)
        )
        resultado = cursor.fetchone()
        conn.close()
 
        if resultado:
            usuario_bd, senha_hash, turma_bd, tipo_bd = resultado
            if check_password_hash(senha_hash, senha):
                session.clear()
                session["usuario_logado"] = usuario_bd
                session["turma"] = turma_bd
                session["tipo"] = tipo_bd or "aluno"
                return redirect("/")
 
        erro = "Usuário ou senha incorretos."
 
    alerta = f'<div class="alert alert-danger py-2 small">{esc(erro)}</div>' if erro else ""
 
    return render_template_string(f'''
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #155888 0%, #0a2e47 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                padding: 20px 0;
            }}
            .login-card {{ border-radius: 20px; border: none; box-shadow: 0 15px 35px rgba(0,0,0,0.2); }}
            .btn-login {{ background: #155888; border: none; padding: 12px; font-weight: bold; transition: 0.3s; }}
            .btn-login:hover {{ background: #1c74b4; transform: scale(1.02); }}
            .school-logo {{ font-size: 3rem; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-12 col-md-4">
                    <div class="card login-card p-4">
                        <div class="text-center">
                            <div class="school-logo">🎓</div>
                            <h4 class="fw-bold" style="color:#155888">CETI Job de Macedo Brito</h4>
                            <p class="text-muted small">Sistema Acadêmico {ANO_FIXO}</p>
                        </div>
                        <hr>
                        {alerta}
                        <form method="POST">
                            {csrf_input()}
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Usuário</label>
                                <input name="usuario" class="form-control form-control-lg" placeholder="Digite seu login" required>
                            </div>
 
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Senha</label>
                                <div class="input-group">
                                    <input type="password" id="campoSenha" name="senha" class="form-control form-control-lg" placeholder="Digite sua senha" required autocomplete="current-password">
                                    <button type="button" class="btn btn-outline-secondary" id="btnMostrarSenha" tabindex="-1">👁️</button>
                                </div>
                            </div>
 
                            <script>
                                document.getElementById('btnMostrarSenha').addEventListener('click', function() {{
                                    const campo = document.getElementById('campoSenha');
                                    if (campo.type === 'password') {{
                                        campo.type = 'text';
                                        this.textContent = '🙈';
                                    }} else {{
                                        campo.type = 'password';
                                        this.textContent = '👁️';
                                    }}
                                }});
                            </script>
 
                            <button class="btn btn-primary btn-login w-100 mt-2">ENTRAR NO SISTEMA</button>
                        </form>
 
                        <div class="text-center mt-3">
                            <a href="/cadastro">Criar uma conta</a>
                        </div>
 
                        <div class="text-center mt-4">
                            <small class="text-muted">Piauí - Educação de Tempo Integral</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''')
 
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
 
 
@app.route("/turmas")
def pagina_turmas():
    if "usuario_logado" not in session:
        return redirect("/login")
    botoes = "".join([f"<a href='/horarios/{t}' class='btn btn-lg mb-3 text-white' style='background:#155888; border:none;'>Turma {t}</a>" for t in horarios_escolares.keys()])
    return render_template_string(f'<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"><body class="bg-light">{gerar_navbar(True)}<div class="container mt-5 text-center"><div class="card shadow p-4 p-md-5 col-12 col-md-6 mx-auto border-0" style="border-radius:20px;"><h3 class="mb-4">Horários {ANO_FIXO}</h3><div class="d-grid">{botoes}</div></div></div></body>')
 
 
@app.route("/horarios/<turma>")
def exibir_horarios(turma):
    if "usuario_logado" not in session:
        return redirect("/login")
 
    grade = horarios_escolares.get(turma)
    if grade is None:
        return redirect("/turmas")
 
    colunas = "".join([
        f"""
        <div class='col'>
            <div class='card shadow-sm'>
                <div class='card-header text-white small' style='background:#155888;'>
                    {dia}
                </div>
                <ul class='list-group list-group-flush'>
                    {"".join(f"<li class='list-group-item small'>{esc(a)}</li>" for a in aulas)}
                </ul>
            </div>
        </div>
        """
        for dia, aulas in grade.items()
    ])
 
    return render_template_string(f'''
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
 
    <body class="bg-light">
        {gerar_navbar(True)}
 
        <div class="container mt-4">
            <h3>Grade Turma {esc(turma)} - {ANO_FIXO}</h3>
 
            <div class="row row-cols-1 row-cols-md-5 g-2 mt-3">
                {colunas}
            </div>
        </div>
    </body>
    ''')
 
 
# ------------------- ÁREA ADMIN -------------------
@app.route("/admin")
def admin_painel():
    if session.get("tipo") != "admin":
        return redirect("/")
 
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT usuario, turma, tipo FROM usuarios ORDER BY tipo, usuario")
    usuarios = cursor.fetchall()
    conn.close()
 
    cor_badge = {"admin": "danger", "professor": "primary", "aluno": "secondary"}
 
    linhas = "".join([f"""
        <tr>
            <td>{esc(u)}</td>
            <td>{esc(t) or '-'}</td>
            <td><span class="badge bg-{cor_badge.get(tp, 'secondary')}">{esc(tp)}</span></td>
            <td>
                <a href="/admin/editar/{esc(u)}" class="btn btn-sm btn-outline-primary">Editar</a>
                {"" if u == "admin" else f'''<form method="POST" action="/admin/excluir/{esc(u)}" style="display:inline;" onsubmit="return confirm('Excluir este usuário?')">{csrf_input()}<button class="btn btn-sm btn-outline-danger">Excluir</button></form>'''}
            </td>
        </tr>
    """ for u, t, tp in usuarios])
 
    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
    {gerar_navbar(True)}
    <div class="container mt-4">
        <div class="card shadow p-3 p-md-4">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <div>
                    <h3 style="color:#155888">⚙️ Área Administrativa</h3>
                    <p class="text-muted">Gerencie usuários, turmas e permissões.</p>
                </div>
                <a href="/admin/avisos" class="btn btn-primary">📣 Gerenciar avisos</a>
            </div>
            <div class="table-responsive">
                <table class="table table-hover align-middle mt-3">
                    <thead><tr><th>Usuário</th><th>Turma</th><th>Tipo</th><th>Ações</th></tr></thead>
                    <tbody>{linhas}</tbody>
                </table>
            </div>
        </div>
    </div>
    </body>
    </html>
    """)
 
 
@app.route("/admin/editar/<usuario>", methods=["GET", "POST"])
def admin_editar_usuario(usuario):
    if session.get("tipo") != "admin":
        return redirect("/")
 
    conn = conectar()
    cursor = conn.cursor()
 
    if request.method == "POST":
        nova_turma = request.form.get("turma") or None
        if nova_turma not in TURMAS_DISPONIVEIS:
            nova_turma = None
        novo_tipo = request.form.get("tipo")
        if novo_tipo not in ("aluno", "professor", "admin"):
            novo_tipo = "aluno"
        if usuario == "admin":
            novo_tipo = "admin"  # evita o admin principal perder o acesso
        cursor.execute(
            "UPDATE usuarios SET turma = ?, tipo = ? WHERE usuario = ?",
            (nova_turma, novo_tipo, usuario)
        )
        conn.commit()
        conn.close()
        return redirect("/admin")
 
    cursor.execute("SELECT turma, tipo FROM usuarios WHERE usuario = ?", (usuario,))
    resultado = cursor.fetchone()
    conn.close()
 
    if not resultado:
        return redirect("/admin")
 
    turma_atual, tipo_atual = resultado
    opcoes_turma = "".join([
        f'<option value="{t}" {"selected" if t == turma_atual else ""}>{t}</option>'
        for t in TURMAS_DISPONIVEIS
    ])
    opcoes_tipo = "".join([
        f'<option value="{t}" {"selected" if t == tipo_atual else ""}>{t.capitalize()}</option>'
        for t in ["aluno", "professor", "admin"]
    ])
 
    return render_template_string(f"""
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <body class="bg-light">
    {gerar_navbar(True)}
    <div class="container mt-5 col-12 col-md-4">
        <div class="card p-4 shadow">
            <h4>Editar {esc(usuario)}</h4>
            <form method="POST">
                {csrf_input()}
                <div class="mb-3">
                    <label class="form-label">Turma</label>
                    <select name="turma" class="form-select">
                        <option value="">-- Nenhuma --</option>
                        {opcoes_turma}
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Tipo</label>
                    <select name="tipo" class="form-select">{opcoes_tipo}</select>
                </div>
                <button class="btn btn-success w-100">Salvar</button>
            </form>
        </div>
    </div>
    </body>
    """)
 
 
@app.route("/admin/excluir/<usuario>", methods=["POST"])
def admin_excluir_usuario(usuario):
    if session.get("tipo") != "admin":
        return redirect("/")
    if usuario == "admin":
        return redirect("/admin")
 
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE usuario = ?", (usuario,))
    conn.commit()
    conn.close()
 
    return redirect("/admin")
 
 
# ------------------- ADMIN: AVISOS POR TURMA -------------------
@app.route("/admin/avisos", methods=["GET", "POST"])
def admin_avisos():
    if session.get("tipo") != "admin":
        return redirect("/")
 
    erro = ""
    if request.method == "POST":
        texto = (request.form.get("texto") or "").strip()
        turmas_escolhidas = request.form.getlist("turmas")
 
        if not texto:
            erro = "Escreva o texto do aviso."
        elif len(texto) > 500:
            erro = "O aviso pode ter no máximo 500 caracteres."
        elif not turmas_escolhidas:
            erro = "Escolha ao menos uma turma (ou 'Todas as turmas')."
        else:
            # "todas" = um único aviso geral (turma NULL); senão, um aviso por turma marcada
            if "todas" in turmas_escolhidas:
                alvos = [None]
            else:
                alvos = [t for t in turmas_escolhidas if t in TURMAS_DISPONIVEIS]
            if not alvos:
                erro = "Turma inválida."
            else:
                agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                conn = conectar()
                cursor = conn.cursor()
                for alvo in alvos:
                    cursor.execute(
                        "INSERT INTO avisos (turma, texto, autor, criado_em) VALUES (?, ?, ?, ?)",
                        (alvo, texto, session["usuario_logado"], agora)
                    )
                conn.commit()
                conn.close()
                return redirect("/admin/avisos")
 
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, turma, texto, autor, criado_em FROM avisos ORDER BY id DESC")
    avisos = cursor.fetchall()
    conn.close()
 
    checks_turmas = "".join([
        f'<div class="form-check form-check-inline"><input class="form-check-input check-turma" type="checkbox" name="turmas" value="{t}" id="t{t}">'
        f'<label class="form-check-label" for="t{t}">{t}</label></div>'
        for t in TURMAS_DISPONIVEIS
    ])
 
    if avisos:
        linhas = "".join([f"""
            <tr>
                <td>{'<span class="badge bg-primary">' + esc(t) + '</span>' if t else '<span class="badge bg-secondary">Todas</span>'}</td>
                <td style="white-space:pre-line">{esc(texto)}</td>
                <td class="small text-muted">{esc(autor)}<br>{esc(criado)}</td>
                <td>
                    <form method="POST" action="/admin/avisos/excluir/{i}" onsubmit="return confirm('Excluir este aviso?')">
                        {csrf_input()}<button class="btn btn-sm btn-outline-danger">Excluir</button>
                    </form>
                </td>
            </tr>
        """ for i, t, texto, autor, criado in avisos])
        tabela = f"""<div class="table-responsive"><table class="table table-hover align-middle">
            <thead><tr><th>Turma</th><th>Aviso</th><th>Publicado</th><th></th></tr></thead>
            <tbody>{linhas}</tbody></table></div>"""
    else:
        tabela = '<p class="text-muted">Nenhum aviso publicado ainda.</p>'
 
    alerta = f'<div class="alert alert-danger py-2">{esc(erro)}</div>' if erro else ""
 
    return render_template_string(f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
    {gerar_navbar(True)}
    <div class="container mt-4 mb-5">
        <div class="card shadow p-3 p-md-4 mb-4">
            <h3 style="color:#155888">📣 Novo aviso</h3>
            <p class="text-muted small">O aviso aparece no mural dos alunos das turmas selecionadas.</p>
            {alerta}
            <form method="POST">
                {csrf_input()}
                <div class="mb-3">
                    <label class="form-label fw-bold">Para quem?</label><br>
                    <div class="form-check form-check-inline">
                        <input class="form-check-input" type="checkbox" name="turmas" value="todas" id="tTodas">
                        <label class="form-check-label fw-bold" for="tTodas">Todas as turmas</label>
                    </div>
                    {checks_turmas}
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">Texto do aviso</label>
                    <textarea name="texto" class="form-control" rows="3" maxlength="500" required></textarea>
                </div>
                <button class="btn btn-success">Publicar aviso</button>
            </form>
        </div>
 
        <div class="card shadow p-3 p-md-4">
            <h4 style="color:#155888">Avisos publicados</h4>
            {tabela}
        </div>
    </div>
    <script>
        // "Todas as turmas" desmarca as turmas individuais e vice-versa
        const todas = document.getElementById('tTodas');
        const individuais = document.querySelectorAll('.check-turma');
        todas.addEventListener('change', () => {{ if (todas.checked) individuais.forEach(c => c.checked = false); }});
        individuais.forEach(c => c.addEventListener('change', () => {{ if (c.checked) todas.checked = false; }}));
    </script>
    </body>
    </html>
    """)
 
 
@app.route("/admin/avisos/excluir/<int:aviso_id>", methods=["POST"])
def admin_excluir_aviso(aviso_id):
    if session.get("tipo") != "admin":
        return redirect("/")
 
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM avisos WHERE id = ?", (aviso_id,))
    conn.commit()
    conn.close()
 
    return redirect("/admin/avisos")
 
 
inicializar_banco()
 
if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
 
