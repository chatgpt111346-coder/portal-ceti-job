from flask import Flask, render_template_string, request, redirect, session, url_for
import calendar
from datetime import datetime

app = Flask(__name__)
app.secret_key = "chave_mestra_escola_2026_seguranca_total"

# --- CONFIGURAÇÕES FIXAS 2026 ---
ANO_FIXO = 2026
USUARIOS_PERMITIDOS = {"admin": "1234", "professor": "piauí2026", "aluno01": "escola123"}
MESES_NOME = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

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
        "Segunda": ["Física (Paulo)", "Física (Paulo)", "Geografia (Erika)", "Geografia (Erika)", "Zootecnia (Erika)", "Zootecnia (Erika)", "Olericultura", "Olericultura"],
        "Terça": ["Agroecologia (Erika)", "Agroecologia (Erika)", "Biologia (Emerson)", "Biologia (Emerson)", "Matemática (Joaquim)", "Matemática (Joaquim)", "Espanhol (Gilmara)", "Artes (Gilmara)"],
        "Quarta": ["Ed. Física (Thais)", "Esportes (Thais)", "História (Denis)", "História (Denis)", "Filosofia (Denis)", "Int. Artes (Emerson)", "Matemática (Joaquim)", "Matemática/Rec (Joaquim)"],
        "Quinta": ["Português (Sorley)", "Português (Sorley)", "Forragicultura (Erika)", "Forragicultura (Erika)", "Sociologia (Erika)", "Olimpíada (Paulo)", "Geoprocessamento (Erika)", "Geoprocessamento (Erika)"],
        "Sexta": ["Leitura/Produção (Sorley)", "Leitura/Produção (Sorley)", "Química (Marcos)", "Química (Marcos)", "Projeto de Vida (Jaqueline)", "Ed. Financeira (Joaquim)", "Inglês (Jaqueline)", "Inglês (Jaqueline)"]
    },
    "1B": {
        "Segunda": ["Geografia (Erika)", "Geografia (Erika)", "Física (Paulo)", "Física (Paulo)", "Inglês (Jacqueline)", "Inglês (Jacqueline)", "Espanhol (Gilmara)", "Artes (Gilmara)"],
        "Terça": ["Biologia (Emerson)", "Biologia (Emerson)", "Esportes (Thais)", "Matemática/Rec (Euclides)", "Sociologia (Erika)", "Int. Artes (Julio)", "Matemática (Joaquim)", "Matemática (Joaquim)"],
        "Quarta": ["Geoprocessamento (Wemerson)", "Geoprocessamento (Wemerson)", "Ed. Física (Thais)", "Olimpíada (Marcos)", "Matemática (Joaquim)", "Ed. Financeira (Joaquim)", "História (Denis)", "História (Denis)"],
        "Quinta": ["Agroecologia (Wemerson)", "Agroecologia (Wemerson)", "Forragicultura (Wemerson)", "Forragicultura (Wemerson)", "Filosofia (Denis)", "Olericultura (Wemerson)", "Leitura/Produção (Sorley)", "Português (Sorley)"],
        "Sexta": ["Zootecnia (Wemerson)", "Zootecnia (Wemerson)", "Português (Sorley)", "Português (Sorley)", "Olericultura (Wemerson)", "Projeto de Vida (Jaqueline)", "Química (Marcos)", "Química (Marcos)"]
    },
    "2B": {
        "Segunda": ["Desenho/Sistemas (Wemerson)", "Desenho/Sistemas (Wemerson)", "Desenho/Sistemas (Wemerson)", "Desenho/Sistemas (Wemerson)", "Espanhol (Gilmara)", "Artes (Gilmara)", "Desenho/Sistemas (Wemerson)", "Desenho/Sistemas (Wemerson)"],
        "Terça": ["Ed. Física (Thais)", "Esportes (Thais)", "Matemática/Rec (Euclides)", "Projeto de Vida (Sorley)", "Biologia (Emerson)", "Biologia (Emerson)", "Geografia (Erika)", "Sociologia (Erika)"],
        "Quarta": ["Filosofia (Denis)", "Int. Artes (Emerson)", "Desenho/Sistemas (Wemerson)", "Desenho/Sistemas (Wemerson)", "Português (Vanessa)", "Português (Vanessa)", "Química (Marcos)", "Química (Marcos)"],
        "Quinta": ["Física (Paulo)", "Física (Paulo)", "Português (Sorley)", "Português (Sorley)", "Matemática (Joaquim)", "História (Denis)", "História (Denis)", "Projeto (Paulo) (*)"],
        "Sexta": ["Química (Marcos)", "Química (Marcos)", "Desenho/Sistemas (Wemerson)", "Desenho/Sistemas (Wemerson)", "Matemática (Joaquim)", "Ed. Financeira (Joaquim)", "Química (Marcos)", "Clube de Leitura (Sorley)"]
    },
    "3A": {
        "Segunda": ["Matemática (Euclides)", "Matemática (Euclides)", "Artes (Gilmara)", "Cultura/Artes (Gilmara)", "Matemática (Euclides)", "Matemática/Rec (Euclides)", "Inglês (Jacqueline)", "Inglês (Jacqueline)"],
        "Terça": ["Desenho/Sistemas (Josean)", "História Estudo (Euclides)", "Desenho/Sistemas (Josean)", "Desenho/Sistemas (Josean)", "Artes (Gilmara)", "Biologia (Erika)", "Ed. Física (Thais)", "Esportes (Thais)"],
        "Quarta": ["Int. Artes (Emerson)", "Filosofia (Denis)", "Ed. Trânsito (Emerson)", "Ed. Trânsito (Emerson)", "Química (Marcos)", "Química (Marcos)", "Português (Vanessa)", "Português (Vanessa)"],
        "Quinta": ["Geografia (Erika)", "Sociologia (Erika)", "Física (Paulo)", "Física (Paulo)", "Português (Vanessa)", "Português (Vanessa)", "Projeto (Paulo)", "Filosofia (Denis)"],
        "Sexta": ["Desenho/Sistemas (Josean)", "Desenho/Sistemas (Josean)", "Desenho/Sistemas (Josean)", "Desenho/Sistemas (Josean)", "Português (Vanessa)", "Português (Vanessa)", "Desenho/Sistemas (Josean)", "Desenho/Sistemas (Josean)"]
    },
    "3B": {
        "Segunda": ["Espanhol (Gilmara)", "Cultura/Artes (Gilmara)", "Matemática (Euclides)", "Matemática (Euclides)", "Física (Paulo)", "Física (Paulo)", "Ed. Física (Thais)", "Esportes (Thais)"],
        "Terça": ["História Estudo (Euclides)", "Desenho/Sistemas (Julio)", "Desenho/Sistemas (Julio)", "Desenho/Sistemas (Julio)", "Desenho/Sistemas (Julio)", "Artes (Gilmara)", "Ed. Trânsito (Emerson)", "Ed. Trânsito (Emerson)"],
        "Quarta": ["Desenho/Sistemas (Julio)", "Desenho/Sistemas (Julio)", "Desenho/Sistemas (Julio)", "Desenho/Sistemas (Julio)", "Int. Artes (Julio)", "História (Denis)", "Geografia (Erika)", "Sociologia (Erika)"],
        "Quinta": ["Desenho/Sistemas (Julio)", "Desenho/Sistemas (Julio)", "Português (Vanessa)", "Português (Vanessa)", "Biologia (Paulo)", "Biologia (Paulo)", "Português (Vanessa)", "Filosofia (Denis)"],
        "Sexta": ["Matemática (Euclides)", "Matemática (Euclides)", "Inglês (Jaqueline)", "Inglês (Jaqueline)", "Química (Marcos)", "Química (Marcos)", "Português/Redação (Vanessa)", "Português/Redação (Vanessa)"]
    }
}

def gerar_navbar(exibir_voltar=False):
    user = session.get("usuario_logado", "Usuário")
    # Alterado: 'href' agora aponta diretamente para a raiz "/"
    seta = '<a href="/" class="text-white me-3" style="text-decoration:none;">&#8592; Início</a>' if exibir_voltar else ""
    return f"""
    <nav class="navbar navbar-dark shadow-sm" style="background:#155888; padding: 12px;">
      <div class="container-fluid">
        <div class="d-flex align-items-center">{seta}<span class="navbar-brand">🎓 Sistema Escolar 2026</span></div>
        <div class="ms-auto text-white me-3 small font-monospace">{user} | <a href="/logout" class="btn btn-danger btn-sm">Sair</a></div>
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
    # 1. Tenta buscar o evento de hoje
    evento_exibir = eventos_fixos.get(mes_atual, {}).get(dia_atual)
    
    if not evento_exibir:
        # 2. Se não tem nada hoje, busca o próximo evento do mês
        eventos_mes = eventos_fixos.get(mes_atual, {})
        proximos_dias = sorted([d for d in eventos_mes.keys() if d > dia_atual])
        if proximos_dias:
            dia_prox = proximos_dias[0]
            evento_exibir = f"Próximo: Dia {dia_prox:02d} - {eventos_mes[dia_prox]}"
        else:
            # 3. Se acabou o mês, manda olhar o calendário
            evento_exibir = "Consulte o calendário para os eventos de 2026."

    return render_template_string(f"""
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            .card-dash {{ border: none; border-radius: 15px; transition: 0.3s; background: white; text-decoration: none !important; color: inherit; }}
            .card-dash:hover {{ transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }}
            .welcome-section {{ background: linear-gradient(45deg, #155888, #2a94d6); color: white; padding: 40px; border-radius: 15px; }}
            .event-card {{ background: #0a2e47; color: #ffca28; border-left: 5px solid #ffca28; min-height: 200px; }}
            .btn-action {{ border-radius: 12px; padding: 20px; }}
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
                    <ul class="list-unstyled">
                        <li class="mb-3">✅ <b>Tempo Integral:</b> Horário de 8 aulas (Manhã e Tarde).</li>
                        <li class="mb-3">📌 <b>Início das Aulas:</b> Confirmado para 19/02/2026.</li>
                        <li class="mb-3">⚠️ <b>Documentação:</b> Verifique sua matrícula na secretaria.</li>
                    </ul>
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
                    <p class="fs-5 fw-bold mb-0">{evento_exibir}</p>
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
    
    if ano != 2026:
        return redirect("/calendario/2026/1")  # Trava o ano

    prev_mes = mes - 1 if mes > 1 else 12
    next_mes = mes + 1 if mes < 12 else 1

    cal = calendar.monthcalendar(2026, mes)
    tabela_html = ""

    for semana in cal:
        linha = "<tr>"
        for i, dia in enumerate(semana):
            if dia == 0:
                linha += "<td></td>"
            else:
                user = session["usuario_logado"]
                info_fixo = eventos_fixos.get(mes, {}).get(dia, "")
                info_privado = eventos_privados.get(user, {}).get(mes, {}).get(dia, "")

                if info_privado:
                    css = "evento-privado"
                    texto = f"<div class='evento-texto'>{info_privado} <a href='/excluir_evento/{mes}/{dia}' style='color:red; font-size:0.7rem;'>[X]</a></div>"
                elif info_fixo:
                    css = "evento"
                    texto = f"<div class='evento-texto'>{info_fixo}</div>"
                else:
                    css = "domingo" if i == 6 else ""
                    texto = ""

                # Destacar o dia de hoje
                if dia == hoje.day and mes == hoje.month:
                    css += " hoje"

                linha += f"<td class='{css}' onclick=\"window.location='/add_evento/{mes}/{dia}'\" style='cursor:pointer;'><b>{dia}</b>{texto}</td>"
        tabela_html += linha + "</tr>"

    return render_template_string(f"""
    <html>
    <head>
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
        </style>
    </head>
    <body class="bg-light">{gerar_navbar(True)}
        <div class="container mt-4">
            <div class="calendario-container">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <a href="/calendario/2026/{prev_mes}" class="btn btn-outline-primary">❮</a>
                    <h2 style="color:#155888">CALENDÁRIO ESCOLAR {MESES_NOME[mes-1]} 2026</h2>
                    <a href="/calendario/2026/{next_mes}" class="btn btn-outline-primary">❯</a>
                </div>
                <table class="table table-bordered">
                    <thead><tr><th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sáb</th><th>Dom</th></tr></thead>
                    <tbody>{tabela_html}</tbody>
                </table>
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
        texto = request.form.get("evento")
        user = session["usuario_logado"]

        if user not in eventos_privados:
            eventos_privados[user] = {}
        if mes not in eventos_privados[user]:
            eventos_privados[user][mes] = {}
        eventos_privados[user][mes][dia] = texto

        return redirect(f"/calendario/2026/{mes}")

    return render_template_string(f"""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <body class="bg-light">
    <div class="container mt-5 col-md-4">
        <div class="card p-4 shadow">
            <h4>Adicionar Evento - {dia}/{mes}/2026</h4>
            <form method="POST">
                <input name="evento" class="form-control mb-3" required>
                <button class="btn btn-success w-100">Salvar</button>
            </form>
        </div>
    </div>
    </body>
    """)

# ------------------- EXCLUIR EVENTO PRIVADO -------------------
@app.route("/excluir_evento/<int:mes>/<int:dia>")
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
    if request.method == "POST":
        user, senha = request.form.get("usuario"), request.form.get("senha")
        if USUARIOS_PERMITIDOS.get(user) == senha:
            session["usuario_logado"] = user
            return redirect("/")
    
    return render_template_string(f'''
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ 
                background: linear-gradient(135deg, #155888 0%, #0a2e47 100%); 
                height: 100vh; 
                display: flex; 
                align-items: center; 
            }}
            .login-card {{
                border-radius: 20px;
                border: none;
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            }}
            .btn-login {{
                background: #155888;
                border: none;
                padding: 12px;
                font-weight: bold;
                transition: 0.3s;
            }}
            .btn-login:hover {{ background: #1c74b4; transform: scale(1.02); }}
            .school-logo {{ font-size: 3rem; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-4">
                    <div class="card login-card p-4">
                        <div class="text-center">
                            <div class="school-logo">🎓</div>
                            <h4 class="fw-bold" style="color:#155888">CETI Job de Macedo Brito</h4>
                            <p class="text-muted small">Sistema Acadêmico {ANO_FIXO}</p>
                        </div>
                        <hr>
                        <form method="POST">
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Usuário</label>
                                <input name="usuario" class="form-control form-control-lg" placeholder="Digite seu login" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Senha</label>
                                <input type="password" name="senha" class="form-control form-control-lg" placeholder="••••••••" required>
                            </div>
                            <button class="btn btn-primary btn-login w-100 mt-2">ENTRAR NO SISTEMA</button>
                        </form>
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
def logout(): session.clear(); return redirect("/login")

@app.route("/turmas")
def pagina_turmas():
    if "usuario_logado" not in session: return redirect("/login")
    botoes = "".join([f"<a href='/horarios/{t}' class='btn btn-lg mb-3 text-white' style='background:#155888; border:none;'>Turma {t}</a>" for t in horarios_escolares.keys()])
    return render_template_string(f'<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"><body class="bg-light">{gerar_navbar(True)}<div class="container mt-5 text-center"><div class="card shadow p-5 col-md-6 mx-auto border-0" style="border-radius:20px;"><h3 class="mb-4">Horários {ANO_FIXO}</h3><div class="d-grid">{botoes}</div></div></div></body>')

@app.route("/horarios/<turma>")
def exibir_horarios(turma):
    if "usuario_logado" not in session: return redirect("/login")
    grade = horarios_escolares.get(turma)
    colunas = "".join([f"<div class='col'><div class='card shadow-sm'><div class='card-header text-white small' style='background:#155888;'>{dia}</div><ul class='list-group list-group-flush'>{''.join([f'<li class=\"list-group-item small\">{a}</li>' for a in aulas])}</ul></div></div>" for dia, aulas in grade.items()])
    return render_template_string(f'<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"><body class="bg-light">{gerar_navbar(True)}<div class="container mt-4"><h3>Grade Turma {turma} - {ANO_FIXO}</h3><div class="row row-cols-1 row-cols-md-5 g-2 mt-3">{colunas}</div></div></body>')

if __name__ == "__main__":
    app.run(debug=True)