from app import app, csrf, db
from flask import render_template, redirect, flash, url_for, request, session, Response, jsonify
from app.forms.associarpaciente import AssociarPaciente
from app.forms.cadastro_form import CadastroForm
from app.forms.login_form import LoginForm
from app.forms.recuperar_senha import RedefinirSenhaForm
from app.forms.dados_paciente import DadosPacienteForm
from app.forms.validarprofissional import ValidarProfissional
from app.services.UsuarioController import UsuarioController
from app.services.AuthenticationController import AuthenticationController
from app.modelos import LeituraTemperatura, Usuario
from app.forms.papel_form import PapelForm
from datetime import date, time
from datetime import datetime, timedelta, timezone
import math
from flask import request, jsonify
from sqlalchemy import func, select

# guarda em memória os dados mais recentes para a interface de acompanhamento
ultima_leitura = {
    "temperatura": "--",
    "status": "Aguardando leitura",
    "hora": "--",
}
ultima = {"temperatura": None, "hora": None}
FUSO_BRASILIA = timezone(timedelta(hours=-3))


# persiste a temperatura recebida e atualiza os dados da última leitura exibidos no site.
def _registrar_leitura_temperatura(valor):
    temperatura = float(valor)
    data_hora = datetime.now(FUSO_BRASILIA).replace(tzinfo=None)
    hora = data_hora.strftime("%d/%m/%Y %H:%M:%S")
    db.session.add(LeituraTemperatura(temperatura=temperatura, data_hora=data_hora))
    db.session.commit()
    ultima_leitura.update({
        "temperatura": temperatura,
        "status": "Leitura recebida",
        "hora": hora,
    })
    ultima.update({"temperatura": temperatura, "hora": hora})


# calcula o ITR diário como a diferença entre a maior e a menor temperatura de cada dia
def _calcular_itr_diario(leituras, hoje):
    temperaturas_por_dia = {
        hoje - timedelta(days=offset): []
        for offset in range(6, -1, -1)
    }
    for leitura in leituras:
        dia = leitura.data_hora.date()
        if dia in temperaturas_por_dia:
            temperaturas_por_dia[dia].append(float(leitura.temperatura))

    return [
        {
            "data": dia.isoformat(),
            "label": dia.strftime("%d/%m"),
            "itr": round(max(temperaturas) - min(temperaturas), 2) if temperaturas else None,
        }
        for dia, temperaturas in temperaturas_por_dia.items()
    ]


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/home")
def home():
    usuario = UsuarioController.buscar_usuario_login() #carregar o dado do nome do usuário -- pode ser outros dados
    if not usuario:
        return redirect(url_for("login"))

    papeis = UsuarioController.listar_papeis_usuario()
    papel_ativo = UsuarioController.obter_papel_ativo()
    if not papel_ativo:
        flash("Sua conta ainda não possui um papel configurado.", "warning")
        return redirect(url_for("questionario"))

    tem_seletor_paciente = papel_ativo in {"cuidador", "responsavel"}
    pacientes_cuidados = (
        UsuarioController.listar_pacientes_acompanhados(papel_ativo)
        if tem_seletor_paciente else []
    )
    paciente_visualizado = None
    registros_glicemicos = []
    if tem_seletor_paciente and pacientes_cuidados:
        paciente_visualizado = next(
            (paciente for paciente in pacientes_cuidados
             if paciente["id"] == session.get("paciente_visualizado_id")),
            pacientes_cuidados[0],
        )
        session["paciente_visualizado_id"] = paciente_visualizado["id"]
        registros_glicemicos = UsuarioController.buscar_registros_glicemia_login(
            paciente_visualizado["usuario_id"]
        )
    elif not tem_seletor_paciente:
        session.pop("paciente_visualizado_id", None)
        registros_glicemicos = UsuarioController.buscar_registros_glicemia_login()

    hoje = datetime.now(FUSO_BRASILIA).date()
    inicio_periodo = datetime.combine(hoje - timedelta(days=6), time.min)
    fim_periodo = datetime.combine(hoje + timedelta(days=1), time.min)
    # busca as leituras recentes do sensor para montar o gráfico semanal de ITR (na homepage)
    leituras_temperatura = db.session.scalars(
        select(LeituraTemperatura)
        .where(
            LeituraTemperatura.data_hora >= inicio_periodo,
            LeituraTemperatura.data_hora < fim_periodo,
        )
        .order_by(LeituraTemperatura.data_hora)
    ).all()
    itr_diario = _calcular_itr_diario(leituras_temperatura, hoje)

    eventos_calendario = UsuarioController.buscar_eventos_calendario_login()
    return render_template(
        "home.html",
        usuario=usuario,
        papeis=papeis,
        papel_ativo=papel_ativo,
        nomes_papeis=UsuarioController.PAPEIS,
        registros_glicemicos=registros_glicemicos,
        itr_diario=itr_diario,
        eventos_calendario=eventos_calendario,
        is_caregiver=papel_ativo == "cuidador",
        has_patient_switcher=tem_seletor_paciente,
        pacientes_cuidados=pacientes_cuidados,
        paciente_visualizado=paciente_visualizado,
    )


@app.route("/home/papel", methods=["POST"])
def selecionar_papel_home():
    if not UsuarioController.buscar_usuario_login():
        return redirect(url_for("login"))

    papel = request.form.get("papel")
    if not UsuarioController.selecionar_papel(papel):
        flash("Não foi possível trocar para esse papel.", "error")
    return redirect(url_for("home"))


@app.route("/home/paciente", methods=["POST"])
def selecionar_paciente_home():
    paciente_id = request.form.get("paciente_id", type=int)
    paciente = UsuarioController.selecionar_paciente_cuidado(paciente_id) if paciente_id else None
    if not paciente:
        flash("Não foi possível trocar para esse paciente.", "error")
    return redirect(url_for("home"))

#criando o evento no calendario
@app.route("/calendario/evento", methods=["POST"])
def criar_evento_calendario():
    sucesso = UsuarioController.criar_evento_calendario(
        titulo=request.form.get("nome"),
        descricao=request.form.get("descricao"),
        data_evento=request.form.get("data"),
        hora_evento=request.form.get("hora"),
        tipo=request.form.get("tipo"),
    )
    flash(
        "Evento salvo com sucesso!" if sucesso else "Não foi possível salvar o evento.",
        "success" if sucesso else "error",
    )
    return redirect(url_for("home"))


# rota pra editar o evento do usuário
@app.route("/calendario/evento/<int:evento_id>/editar", methods=["POST"])
def editar_evento_calendario(evento_id):
    sucesso = UsuarioController.editar_evento_calendario(
        evento_id=evento_id,
        titulo=request.form.get("nome"),
        descricao=request.form.get("descricao"),
        data_evento=request.form.get("data"),
        hora_evento=request.form.get("hora"),
        tipo=request.form.get("tipo"),
    )
    flash(
        "Evento atualizado com sucesso!" if sucesso else "Não foi possível atualizar o evento.",
        "success" if sucesso else "error",
    )
    return redirect(url_for("home"))

@app.route("/calendario/evento/<int:evento_id>/excluir", methods=["POST"])
def excluir_evento_calendario(evento_id):
    sucesso = UsuarioController.excluir_evento_calendario(evento_id)
    flash(
        "Evento excluído com sucesso!" if sucesso else "Não foi possível excluir o evento.",
        "success" if sucesso else "error",
    )
    return redirect(url_for("home"))

@app.route("/registroglicemia", methods=["GET", "POST"])
def registroglicemia():
    papel_ativo = UsuarioController.obter_papel_ativo()
    if not papel_ativo:
        return redirect(url_for("login"))

    pode_escolher_paciente = papel_ativo in {"cuidador", "responsavel"}
    pacientes_cuidados = (
        UsuarioController.listar_pacientes_acompanhados(papel_ativo)
        if pode_escolher_paciente else []
    )

    if pode_escolher_paciente and not pacientes_cuidados:
        flash("Associe um paciente antes de registrar uma glicemia.", "warning")
        return redirect(url_for("quest_verificar_paciente"))

    if request.method == "POST":
        sucesso = UsuarioController.registrar_glicemia(
            data_registro=request.form.get("data"),
            hora_registro=request.form.get("hora"),
            medida=request.form.get("glicemia"),
            estado=request.form.get("estado"),
            paciente_id=request.form.get("paciente_id"),
        )
        if sucesso:
            flash("Registro glicêmico salvo com sucesso!", "success")
        else:
            flash("Não foi possível salvar o registro glicêmico. Confira o paciente selecionado.", "error")
        parametros = {"data": request.form.get("data", "")}
        if pode_escolher_paciente and request.form.get("paciente_id"):
            parametros["paciente_id"] = request.form.get("paciente_id")
        return redirect(url_for("registroglicemia", **parametros))

    paciente_selecionado_id = None
    if pode_escolher_paciente and pacientes_cuidados:
        paciente_selecionado_id = request.args.get("paciente_id", type=int)
        ids_pacientes = {paciente["id"] for paciente in pacientes_cuidados}
        if paciente_selecionado_id not in ids_pacientes:
            paciente_selecionado_id = session.get("paciente_visualizado_id")
        if paciente_selecionado_id not in ids_pacientes:
            paciente_selecionado_id = pacientes_cuidados[0]["id"]

    return render_template(
        "registroglicemia.html",
        data_inicial=request.args.get("data", ""),
        can_select_patient=pode_escolher_paciente,
        pacientes_cuidados=pacientes_cuidados,
        paciente_selecionado_id=paciente_selecionado_id,
    )


# exibe o acompanhamento do pé diabético e aceita uma leitura de temperatura em JSON
@app.route("/pediabetico", methods=["GET", "POST"])
@csrf.exempt
def pediabetico():
    if request.method == "POST":
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict) or "temperatura" not in dados:
            return jsonify(sucesso=False, erro="Campo 'temperatura' ausente."), 400

        try:
            temperatura = float(dados["temperatura"])
        except (TypeError, ValueError):
            return jsonify(sucesso=False, erro="Temperatura inválida."), 400

        if not math.isfinite(temperatura):
            return jsonify(sucesso=False, erro="Temperatura inválida."), 400

        _registrar_leitura_temperatura(temperatura)
        return jsonify(sucesso=True), 200

    return render_template(
        "pediabetico.html",
        leitura=ultima_leitura,
        hora_temperatura=ultima["hora"],
    )

# mostra na página a última leitura para que a interface atualize temperatura, horário e status
@app.route("/pediabetico/atualizar", methods=["GET"])
def atualizar_leitura_pediabetico():
    return jsonify(ultima_leitura)


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    formCadastro = CadastroForm()
    if formCadastro.validate_on_submit():
        if UsuarioController.email_em_uso(formCadastro.email.data):
            formCadastro.email.errors.append("Este e-mail já está cadastrado.")
        elif UsuarioController.cadastro(formCadastro):
            return redirect(url_for("questionario"))
        else:
            flash("Erro ao criar a conta. Tente novamente.", "error")
    return render_template("cadastro.html", form=formCadastro)


@app.route("/login", methods=["GET", "POST"])
def login():
    formLogin = LoginForm()
    if formLogin.validate_on_submit():
        if AuthenticationController.login(formLogin):
            return redirect(url_for("home")) #vai para a PÁGINA INICIAL depois do gin
        else:
            flash("Usuário ou senha incorretos.", "error")

    return render_template("login.html", title="Login", form=formLogin)


@app.route("/recuperar-senha", methods=["GET", "POST"])
def esqueceu_senha():
    form = RedefinirSenhaForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        usuario = db.session.scalars(
            select(Usuario).where(func.lower(Usuario.email) == email)
        ).first()
        if not usuario:
            form.email.errors.append("Não encontramos uma conta com esse e-mail.")
        elif AuthenticationController.redefinir_senha(usuario, form.nova_senha.data):
            flash("Senha alterada com sucesso. Entre com sua nova senha.", "success")
            return redirect(url_for("login"))
        else:
            flash("Não foi possível alterar a senha. Tente novamente.", "error")

    return render_template("recuperar_senha.html", form=form)

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "warning")
    return redirect(url_for("login"))

@app.route("/questionario", methods=["GET", "POST"])
def questionario():
    form_papel = PapelForm()
    if form_papel.validate_on_submit():
        if UsuarioController.salvar_papeis(form_papel.papeis.data):
            if 'paciente' in form_papel.papeis.data:
                return redirect(url_for("questionario_paciente"))
            if 'cuidador' in form_papel.papeis.data:
                return redirect(url_for("quest_tipo_cuidador"))
            if 'responsavel' in form_papel.papeis.data:
                return redirect(url_for("quest_responsavel"))
            return redirect(url_for("inicio"))
        else:
            flash("Erro ao salvar os papéis no banco.", "error")

    return render_template("questionario.html", form=form_papel)


@app.route("/questionario/paciente", methods=["GET", "POST"])
def questionario_paciente():
    sobre_paciente = request.args.get("para_paciente") == "1"
    form_paciente = DadosPacienteForm()
    if form_paciente.validate_on_submit():
        nome_paciente = (form_paciente.nome.data or "").strip()
        if sobre_paciente and not nome_paciente:
            form_paciente.nome.errors.append("Informe o nome do paciente.")
        elif sobre_paciente and UsuarioController.cadastrar_paciente_acompanhado(
            form_paciente,
            nome_paciente,
        ):
            return redirect(url_for("home"))
        elif not sobre_paciente and UsuarioController.salvar_questionario_paciente(form_paciente):
            return redirect(url_for("home"))
        else:
            flash("Não foi possível salvar os dados do paciente.", "error")

    return render_template(
        "quest_paciente.html",
        form=form_paciente,
        sobre_paciente=sobre_paciente,
    )

@app.route("/questionario/tipo_cuidador", methods=["GET", "POST"])
def quest_tipo_cuidador():
    if request.method == "POST":
        tipo_cuidador = request.form.get("tipo_cuidador")
        UsuarioController.salvar_tipo_cuidador(tipo_cuidador)
        if tipo_cuidador == "profissional":
            print('selecionou prof')
            return redirect(
                url_for("validar_profissional", tipo_cuidador=tipo_cuidador)
            )
        elif tipo_cuidador == "familiar":
            return redirect(
                url_for("quest_verificar_paciente", tipo_cuidador=tipo_cuidador)
            )
    return render_template("tipo_cuidador.html")

@app.route("/verificar_paciente", methods=["GET", "POST"])
def quest_verificar_paciente():
    papel_ativo = UsuarioController.obter_papel_ativo()
    if papel_ativo not in {"cuidador", "responsavel"}:
        flash("Selecione o papel de cuidador ou responsável para associar um paciente.", "warning")
        return redirect(url_for("home"))

    formAssociarPaciente = AssociarPaciente()
    requisicao_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        if not formAssociarPaciente.validate_on_submit():
            mensagem = formAssociarPaciente.email.errors[0] if formAssociarPaciente.email.errors else "Confira o email informado."
            if requisicao_ajax:
                return jsonify(success=False, message=mensagem), 400
        else:
            relacao = request.form.get("relacao_responsavel") or session.get("relacao_responsavel")
            resultado = UsuarioController.associar_paciente(
                formAssociarPaciente.email.data,
                relacao=relacao,
            )
            if resultado in {"success", "already_linked"}:
                if requisicao_ajax:
                    return jsonify(success=True, redirect=url_for("home"))
                return redirect(url_for("home"))

            mensagem = (
                "Não encontramos um paciente cadastrado com esse email."
                if resultado == "not_found"
                else "Confira a relação selecionada para esse paciente."
                if resultado == "invalid_relation"
                else "Não foi possível associar o paciente. Tente novamente."
            )
            if requisicao_ajax:
                status = 404 if resultado == "not_found" else 400 if resultado == "invalid_relation" else 500
                return jsonify(success=False, message=mensagem), status
            flash(mensagem, "error")

    responsavel = UsuarioController.buscar_responsavel_login() if papel_ativo == "responsavel" else None
    relacao = session.get("relacao_responsavel", "")
    relacoes_disponiveis = []
    if responsavel:
        tipo_responsabilidade = getattr(responsavel.responsabilidade, "value", responsavel.responsabilidade)
        if tipo_responsabilidade in {"menor_idade", "curatelado"}:
            session["tipo_responsavel"] = tipo_responsabilidade
        relacoes_disponiveis = ["Pai", "Mãe", "Tia", "Tio", "Avó", "Avô", "Outro"]
        if relacao not in relacoes_disponiveis:
            relacao = ""
    return render_template(
        "verif_paciente.html",
        form=formAssociarPaciente,
        is_responsible=bool(responsavel),
        relacao_responsavel=relacao,
        relacoes_disponiveis=relacoes_disponiveis,
    )

@app.route("/validar_profissional", methods=["GET", "POST"])
def validar_profissional():
    formValidarProf = ValidarProfissional()
    if formValidarProf.validate_on_submit():
        conselho = formValidarProf.conselhoprofissional.data
        registro = formValidarProf.registroprofissional.data
        UsuarioController.salvar_dados_profissional(conselho, registro)
        return redirect(url_for("quest_verificar_paciente"))
    
    return render_template("validar_profissional.html", form=formValidarProf)

@app.route("/questionario/quest_responsavel", methods=["GET", "POST"])
def quest_responsavel():
    if request.method == "POST":
        tipo_responsavel = request.form.get("tipo_responsavel")
        relacao = request.form.get("relacao_responsavel")
        relacoes_validas = {"Pai", "Mãe", "Tia", "Tio", "Avó", "Avô", "Outro"}
        if relacao not in relacoes_validas:
            flash("Selecione uma relação válida para continuar.", "error")
            return redirect(url_for("quest_responsavel"))
        if not UsuarioController.salvar_responsabilidade(tipo_responsavel):
            flash("Não foi possível salvar os dados do responsável.", "error")
            return redirect(url_for("quest_responsavel"))
        session["relacao_responsavel"] = relacao
        return redirect(url_for("quest_verificar_paciente"))
    return render_template("quest_responsavel.html")


@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    usuario = UsuarioController.buscar_usuario_login()
    if not usuario:
        flash("Sua sessão expirou. Faça login novamente.", "error")
        return redirect(url_for("login"))

    papel_ativo = UsuarioController.obter_papel_ativo()
    cuidador = UsuarioController.buscar_cuidador_login() if papel_ativo == "cuidador" else None
    responsavel = UsuarioController.buscar_responsavel_login() if papel_ativo == "responsavel" else None
    if request.method == "POST":
        if cuidador:
            sucesso, mensagem = UsuarioController.atualizar_perfil_cuidador(
                nome=request.form.get("nome"),
                email=request.form.get("email"),
                conselho=request.form.get("conselho_profissional"),
                registro=request.form.get("registro_profissional"),
                foto=request.files.get("foto_perfil"),
            )
        elif responsavel:
            sucesso, mensagem = UsuarioController.atualizar_perfil_responsavel(
                nome=request.form.get("nome"),
                email=request.form.get("email"),
                foto=request.files.get("foto_perfil"),
            )
        else:
            sucesso, mensagem = UsuarioController.atualizar_perfil(
                nome=request.form.get("nome"),
                email=request.form.get("email"),
                peso=request.form.get("peso"),
                genero=request.form.get("genero"),
                tipo_diabete=request.form.get("tipo_diabete"),
                foto=request.files.get("foto_perfil"),
            )
        flash(mensagem, "success" if sucesso else "error")
        if sucesso:
            return redirect(url_for("perfil"))

    if cuidador:
        tipo_cuidador = getattr(cuidador.tipo_cuidador, "value", cuidador.tipo_cuidador)
        return render_template(
            'editperfil.html',
            usuario=usuario,
            cuidador=cuidador,
            is_caregiver=True,
            is_professional_caregiver=tipo_cuidador == "profissional",
        )

    if responsavel:
        return render_template(
            'editperfil.html',
            usuario=usuario,
            is_caregiver=False,
            is_responsible=True,
            is_professional_caregiver=False,
            pacientes_responsaveis=UsuarioController.listar_pacientes_responsavel(),
        )

    paciente, genero, tipo_diabete, idade = UsuarioController.buscar_paciente_login()
    return render_template(
        'editperfil.html', 
        usuario=usuario, 
        is_caregiver=False,
        is_responsible=False,
        paciente=paciente, 
        genero=genero,
        genero_valor=paciente.genero if paciente else '',
        tipo_diabete=tipo_diabete,
        tipo_diabete_valor=paciente.tipo_diabete.value if paciente and paciente.tipo_diabete else '',
        idade=idade
    )


@app.route('/perfil/responsavel/paciente/<int:paciente_id>/desativar', methods=['POST'])
def desativar_vinculo_responsavel(paciente_id):
    sucesso = UsuarioController.desativar_vinculo_responsavel(paciente_id)
    if sucesso:
        flash("A relação foi desativada. O paciente não aparece mais nos seus dados.", "success")
    else:
        flash("Não foi possível desativar essa relação.", "error")
    return redirect(url_for("perfil"))

@app.route('/foto-perfil')
def foto_perfil():
    usuario = UsuarioController.buscar_usuario_login()

    if not usuario or not usuario.foto_perfil:
        return redirect(url_for('static', filename='img/avatar_borda.png'))

    return Response(usuario.foto_perfil, mimetype=usuario.foto_perfil_tipo or 'image/jpeg')


# recebe temperatura via POST e retorna a última leitura via GET.
@app.route("/temperatura", methods=["GET", "POST"])
@csrf.exempt
def receber_temperatura():
    if request.method == "GET":
        dados = request.get_json(silent=True) or {}
        print("Dados recebidos:", dados)
        return jsonify(ultima)

    dados = request.get_json(silent=True) or {}
    print("Dados recebidos:", dados) 
    temp = dados.get("temperatura")
    if temp is None:
        return {"erro": "campo 'temperatura' ausente"}, 400
    try:
        temperatura = float(temp)
    except (TypeError, ValueError):
        return {"erro": "temperatura inválida"}, 400
    if not math.isfinite(temperatura):
        return {"erro": "temperatura inválida"}, 400
    _registrar_leitura_temperatura(temperatura)
    return {"ok": True}
