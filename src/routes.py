from flask import Blueprint, g, render_template, request, jsonify
from modules.utils import find_num_linhas_alterado_ficheiro_repositorio, find_functions, calculo_diffs_diarios, consulta_base_de_dados, trata_categorias, trata_missing, trata_info_vulnerabidade, obter_id_projeto, obter_projeto_com_id

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    """Página inicial do dashboard.
       Renderiza o HTML sem qualquer tipo de parâmetro.
    """
    return render_template('home.html')

@bp.route("/overview_vulnerabilities/", methods =["GET"])
def overview_vulnerabilities():
    """ Route para a página de vulnerabilidades.

        Args:
            Dentro do request.args temos:
                Page (str): página
                Projeto (str): projeto
                Categoria (str): categorias
                Missing (str): missing
    """
    
    # Obtemos a informação dos parâmetro e transformamos tudo em tuplos
    projeto = request.args.get("Projeto").strip(" ").split(" & ")
    projeto.append(" ")
    if not projeto or "All" in projeto or "" in projeto:
        projeto = tuple(["", ""])
    else:
        projeto = tuple(projeto)
    categoria = request.args.get("Categoria").strip(" ").split(" & ")
    if not categoria or "All" in categoria or "" in categoria:
        categoria = tuple(["", ""])
        where_clause = ""
    else:
        categoria = tuple(categoria)
        
        # Contruímos uma condição para puder comparar todos os valores que nos foram passados
        where_clause = " OR " + " OR ".join([f"V_CLASSIFICATION LIKE '%{word}%'" for word in categoria])
        
    missing = request.args.get("Missing").strip(" ").split(" & ")
    if not missing or "All" in missing or "" in missing:
        where_condicao: str = ""
    else:
        where_condicao: str = "AND"
        if "Valid" in missing and len(missing) == 1:
            where_condicao += " MISSING IS NULL"
        elif "Valid" in missing:
            where_condicao += " MISSING IS NULL"
            missing = tuple(missing)
            where_condicao += f""" OR (MISSING IN {missing} OR "{missing}" = "('', '')") """
        else:
            missing.append(" ")
            missing = tuple(missing)
            where_condicao += f""" (MISSING IN {missing} OR "{missing}" = "('', '')") """
            
    offset = request.args.get("Page")
    size = 15
    if offset is None:
        offset = 0
    else:
        offset = (int(offset) - 1) * size

    resultados = consulta_base_de_dados(f"""SELECT PROJECT, CVE, V_CLASSIFICATION, MISSING, VULNERABILITIES.V_ID
                                        FROM VULNERABILITIES 
                                        LEFT JOIN REPOSITORIES_SAMPLE ON VULNERABILITIES.R_ID = REPOSITORIES_SAMPLE.R_ID
                                        WHERE (PROJECT IN {projeto} OR "{projeto}" = "('', '')")
                                        AND ("{categoria}" = "('', '')" {where_clause})
                                        {where_condicao} ORDER BY CVE DESC;
                                        """)

    info = {"Resultados": [], "FiltrosProjetos": [], "FiltrosCategorias": [], "FiltrosMissing": [], "ValoresVulnerabilidade": [f"{offset + 1} to {offset + size}", len(resultados)]}
    resultados = resultados[offset : offset + size]
    
    infoProjetos = consulta_base_de_dados(f""" SELECT PROJECT FROM REPOSITORIES_SAMPLE;""")
    infoCategorias = consulta_base_de_dados(f""" SELECT DISTINCT(V_CLASSIFICATION) FROM VULNERABILITIES;""")
    infoMissing = consulta_base_de_dados(f""" SELECT DISTINCT(MISSING) FROM VULNERABILITIES;""")
    
    for linha in resultados:
        info["Resultados"].append([linha[1], trata_categorias(linha[2]), linha[0], trata_missing(linha[3]), linha[4]])
    for linha in infoProjetos:
        info["FiltrosProjetos"].append(linha[0])
    for linha in infoMissing:
        if linha[0] is None:
            continue
        info["FiltrosMissing"].append(linha[0])
    for linha in infoCategorias:
        help_ = trata_categorias(linha[0]).split(" | ")
        for cat in help_:
            if cat.title() not in info["FiltrosCategorias"]:
                info["FiltrosCategorias"].append(cat.title())
    return render_template("vulnerabilities_results.html", resultados=info)

@bp.route("/overview_patches/patch", methods =["GET"])
def overview_patch_info():
    """Recebemos um patch e vamos buscar a informação sobre ele.
    
    Args:
            Dentro do request.args temos:
                info (str): array com p_ids mas binários
                commit (str): commit a pesquisar
                projeto (str): projeto a pesquisar
    """
    # Ler o que recebemos
    info_json = request.args.get('info')
    commit = request.args.get('commit')
    projeto = request.args.get('projeto')
    try:
        info_array = jsonify(info_json).get_data() if info_json else []
        info_array = info_array.decode('utf-8').strip(r' " \ []').split('"')
    except Exception as e:
        info_array = []
    
    dic: dict = {"Resultados": [], "Tamanho": 0, "Commit": commit, "Projeto": "", "CVE": []}
    
    for p_id in info_array:
        try:
            p_id = p_id.strip("\\[]\n")
            function = find_functions(p_id, projeto)
            dic["Resultados"] += function["data"]
        except Exception as e:
            print(f"Erro no p_id {p_id}: {e}")

    for file in dic["Resultados"]:
        try:
            changes = find_num_linhas_alterado_ficheiro_repositorio(obter_projeto_com_id(file[1]), commit, file[4])
            file.append(changes["adicionadas"])
            file.append(changes["removidas"])
        except Exception as e:
            file.append(0)
            file.append(0)
        
    dic["Tamanho"] = len(dic["Resultados"])
    dic["Projeto"] = projeto

    # CVE relacionados
    resultados = consulta_base_de_dados(f"""SELECT DISTINCT V.CVE, V.V_ID
                                        FROM VULNERABILITIES V
                                        JOIN PATCHES P ON V.V_ID = P.V_ID
                                        WHERE P.P_COMMIT = '{commit}';
                                        """)
    print(resultados)
    for cve, v_id in resultados:
        if cve:
            dic["CVE"].append([cve, v_id])

    return render_template("patch_overview.html", resultados=dic)

@bp.route("/overview_patches/", methods =["GET"])
def overview_patches():
    """ Tratamos dos patches.
        Pode ser feita a pesquisa de todos ou por projeto.
        
        Args:
            Dentro do request.args temos:
                Projeto (str): projeto usado na pesquisa
                Page (str): página
    """
    
    # Procuramos o projeto e a página a ser utilizados
    projeto = request.args.get("Projeto").strip(" ").split(" & ")
    projeto.append(" ")
    if not projeto or "All" in projeto or "" in projeto:
        projeto = tuple(["", ""])
    else:
        projeto = tuple(projeto)
    offset = request.args.get("Page")
    size = 15
    if offset is None:
        offset = 0
    else:
        offset = (int(offset) - 1) * size
        
    # Obtemos a informação geral da base de dados sobre patches
    resultados = consulta_base_de_dados(f"""SELECT DISTINCT(P_COMMIT), PROJECT
                                        FROM PATCHES 
                                        LEFT JOIN REPOSITORIES_SAMPLE ON PATCHES.R_ID = REPOSITORIES_SAMPLE.R_ID
                                        WHERE PROJECT IN {projeto} OR "{projeto}" = "('', '')";
                                        """)

    info = {"Resultados": [], "FiltrosProjetos": [], "ValoresPatches": [f"{offset + 1} to {offset + size}", len(resultados)]}
    resultados = resultados[offset : offset + size]
    infoProjetos = consulta_base_de_dados(f""" SELECT PROJECT FROM REPOSITORIES_SAMPLE;""")
    
    for linha in resultados:
        info["Resultados"].append([linha[1], linha[0]])
    for linha in infoProjetos:
        info["FiltrosProjetos"].append(linha[0])
        
    return render_template("patches_results.html", resultados=info)

@bp.route("/overview_cwes/", methods=["GET"])
def overview_cwes():
    """ Trata-se das cwes do dataset.
        São apresentadas todas as cwe, assim como o número de vezes que aparecem
        e algumas informações extra.
        
        Args:
            Dentro do request.args temos:
                CWE (str): cwe pesquisada
                Categoria (str): categorias a pesquisar

    """
    
    # Tentamos obter a cwe
    categoria = request.args.get("Categoria").strip(" ").split(" & ")
    categoria.append(" ")
    if not categoria or "All" in categoria or "" in categoria:
        categoria = tuple(["", ""])
    else:
        categoria = tuple(categoria)
    cwe_filter = request.args.get("CWE")
    if cwe_filter is None:
        cwe_filter = [""]
    else:
        cwe_filter = cwe_filter.split(",")
    offset = request.args.get("Page")
    size = 15
    if offset is None:
        offset = 0
    else:
        offset = (int(offset) - 1) * size
        
    # Procuramos a informação
    cwes: list = []
    for cwe in cwe_filter:
        cwes += consulta_base_de_dados(f"""SELECT CWE_INFO.V_CWE, CWE_INFO.DESCRIPTION, VULNERABILITY_CATEGORY.NAME , COALESCE(counter.count, 0) as "contagem"
                                     FROM CWE_INFO
                                     LEFT JOIN VULNERABILITY_CATEGORY 
                                     ON VULNERABILITY_CATEGORY.ID_CATEGORY = CWE_INFO.ID_CATEGORY 
                                     LEFT JOIN (SELECT V_CWE, COUNT(*) as count FROM VULNERABILITIES_CWE WHERE V_CWE = '{cwe}' OR '{cwe}' = '' GROUP BY V_CWE) AS counter ON CWE_INFO.V_CWE = counter.V_CWE
                                     WHERE (CWE_INFO.V_CWE = '{cwe}' OR '{cwe}' = '' )
                                     AND (VULNERABILITY_CATEGORY.NAME IN {categoria} OR "{categoria}" = "('', '')")
                                     ORDER BY contagem DESC;
                                     """)
    
    dic: dict = {"CWES": {}, "FiltrosCategorias": [], "ContagemCategorias" : [], "ValoresCWE": [f"{offset + 1} to {offset + size}", len(cwes)]}
    cwes = cwes[offset : offset + size]
    infoCategorias = consulta_base_de_dados(f"""SELECT VULNERABILITY_CATEGORY.NAME, COUNT(CWE_INFO.V_CWE)
                                    FROM VULNERABILITY_CATEGORY
                                    LEFT JOIN CWE_INFO 
                                    ON VULNERABILITY_CATEGORY.ID_CATEGORY = CWE_INFO.ID_CATEGORY
                                    GROUP BY VULNERABILITY_CATEGORY.NAME;""")

    # Adicionamos CWE ao numero para uma melhor leitura
    for linha in cwes:
        chave = linha[0]
        if "CWE-" + chave not in dic.keys():
            dic["CWES"]["CWE-" + chave] = [linha[3], linha[1], linha[2]]
    for linha in infoCategorias:
        dic["FiltrosCategorias"].append(linha[0])
        dic["ContagemCategorias"].append(linha[1])

    return render_template("cwes_results.html", resultados = dic)

@bp.route("/daily_update/")
def daily_update():
    """Obtemos a informação do último dia de atualizações.

    Returns:
        resultados: dicionário com a Data e Informação de cada projeto {DATA: DD-MM-YYY, INFO: {PROJETO: [0,0,0,0] ... }}
    """
    # Obtemos toda a informação do dia mais atualizado possivel
    # Ordem alfabética, atualizadas, desaparecidas, iguais, novas
    info, data = calculo_diffs_diarios()
    dic: dict = {"Data": [str(data)], "Info": info}

    return render_template("daily_update.html", resultados = dic)

@bp.route("/resumeflask/", methods=["GET"])
def resumeflask():
    """ Route para a página de resumo da base de dados.
        Obtemos informação geral sobre o que se passa na mesma.
        
        Args:
            Dentro do request.args temos:
                Projeto (str): projeto usado na pesquisa
    """
    
    # Tentamos identificar o projeto, se não conseguirmos usamos todos
    projeto = request.args.get("Projeto").strip(" ").split(" & ")
    projeto.append(" ")
    if not projeto or "All" in projeto or "" in projeto:
        lista_r_id = tuple(["", ""])
    else:
        projeto = tuple(projeto)
        
        lista_r_id = []
        for projeto_nome in projeto:
            lista_r_id.append(obter_id_projeto(projeto_nome))
        lista_r_id = tuple(lista_r_id)
    
    # Obter os valores
    vulnerabilidades = consulta_base_de_dados(f"""SELECT COUNT(*) FROM VULNERABILITIES WHERE R_ID IN {lista_r_id} OR "{lista_r_id}" = "('', '')";""")
    patches = consulta_base_de_dados(f"""SELECT COUNT(DISTINCT(P_COMMIT)) FROM PATCHES WHERE R_ID IN {lista_r_id} OR "{lista_r_id}" = "('', '')";""")
    cwes = consulta_base_de_dados(f"""SELECT COUNT(*) FROM CWE_INFO WHERE V_CWE IN (SELECT V_CWE FROM VULNERABILITIES_CWE WHERE V_ID IN (SELECT V_ID FROM VULNERABILITIES WHERE R_ID IN {lista_r_id})) OR "{lista_r_id}" = "('', '')";""")
    projetos = consulta_base_de_dados(f"""SELECT COUNT(*) FROM REPOSITORIES_SAMPLE WHERE R_ID IN {lista_r_id} OR "{lista_r_id}" = "('', '')";""")
    infoCategorias = consulta_base_de_dados(f"""SELECT VULNERABILITY_CATEGORY.NAME FROM VULNERABILITY_CATEGORY""")

    # Construir a lista de resultados
    dic: dict = {"FiltrosProjetos": [], "FiltrosCategorias": []}
    dic_auxiliar: dict = {}

    dic_auxiliar["Vulnerabilities"] = vulnerabilidades[0][0]
    dic_auxiliar["Patches"] = patches[0][0]
    dic_auxiliar["CWEs"] = cwes[0][0]
    dic_auxiliar["Projects"] = projetos[0][0]
    dic['resultados'] = dic_auxiliar
    
    infoProjetos = consulta_base_de_dados(f""" SELECT PROJECT FROM REPOSITORIES_SAMPLE;""")
    
    for linha in infoProjetos:
        dic["FiltrosProjetos"].append(linha[0])

    categorias_comuns = getattr(g, 'categorias_comuns', None)
    if categorias_comuns:
        dic["FiltrosCategorias"] = categorias_comuns
    else:
        for linha in infoCategorias:
            dic["FiltrosCategorias"].append(linha[0])

    return render_template("resume.html", resultados=dic)

@bp.route("/overview_vulnerability/", methods=["GET"])
def overview_vulnerability():
    """ Route onde se mostra toda a informação sorbe uma determinada vulnerabilidade referenciada pelo seu id na base de dados.

        Args:
            Dentro do request.args temos:
                id (str): id da vulnerabilidade
    """
    
    # Lemos o id e passamos para inteiro
    v_id = int(request.args.get("id"))

    # Obtemos toda a informação com atenção para o caso de não haver cwes
    info = consulta_base_de_dados(f"""SELECT CVE, V_CLASSIFICATION, VULNERABILITY_URL, MISSING, PROJECT FROM VULNERABILITIES LEFT JOIN REPOSITORIES_SAMPLE ON REPOSITORIES_SAMPLE.R_ID = VULNERABILITIES.R_ID WHERE V_ID = {v_id};""")
    info2 = consulta_base_de_dados(f"""SELECT P_URL, P_COMMIT FROM PATCHES WHERE V_ID = {v_id};""")
    info3 = consulta_base_de_dados(f"""SELECT VULNERABILITIES_CWE.V_CWE, DESCRIPTION, ID_CATEGORY FROM VULNERABILITIES_CWE LEFT JOIN CWE_INFO ON CWE_INFO.V_CWE = VULNERABILITIES_CWE.V_CWE WHERE V_ID = {v_id};""")

    if len(info3) > 0 and info3[0][2] is not None:
        info4 = consulta_base_de_dados(f"""SELECT NAME FROM VULNERABILITY_CATEGORY WHERE ID_CATEGORY = {info3[0][2]};""")
    else:
        info4: list = ["-"]    
    info5 = consulta_base_de_dados(f"""SELECT * FROM VETORES WHERE V_ID = {v_id};""")
    
    dic: dict = {"Vulnerabilidades": [], "Patches": [], "CWE": [], "Categoria": [], "Vetores": []}
    for linha in info:
        dic["Vulnerabilidades"].append([linha[0], trata_categorias(linha[1]), linha[2], trata_missing(linha[3]), linha[4]])
    for linha in info2:
        dic["Patches"].append([linha[0], linha[1]])
    for linha in info3:
        dic["CWE"].append([linha[0], linha[1]])
    for linha in info4:
        dic["Categoria"].append([linha[0]])
        print(dic["Categoria"])
    for linha in info5:
        dic["Vetores"].append([linha[0], linha[1], linha[2], linha[3], linha[4], linha[5], linha[6], linha[7], linha[8], linha[9], linha[10], linha[11], linha[12], linha[14], linha[15], linha[16], linha[17], linha[18]])
    
    # Removemos os Nones do dicionário
    dic = trata_info_vulnerabidade(dic)
    
    return render_template("overview_vulnerability.html", resultados = dic)

@bp.route("/grafico/", methods=["GET"])
def grafico():
    """ Route para a página de resumo da base de dados.
        Este endpoint apenas serve para recolher a informação do gráfico.
        
        Args:
            Dentro do request.args temos:
                Projeto (str): projeto usado na pesquisa
                Cwes (str): cwes pedidas (opcional)
        Returns:
            Passamos em JSON:
                dic (dic|JSON): dicionário com todas as cwes mais comuns e a sua contagem por ano
    """
    
    # Obtemos a informação de um projeto
    projeto = request.args.get("Projeto").strip(" ").split(" & ")
    projeto.append(" ")
    if not projeto or "All" in projeto or "" in projeto:
        lista_r_id = tuple(["", ""])
    else:
        projeto = tuple(projeto)
        
        lista_r_id = []
        for projeto_nome in projeto:
            lista_r_id.append(obter_id_projeto(projeto_nome))
        lista_r_id = tuple(lista_r_id)
            
    dic: dict = {"Data": [], "Titulos": []}

    cwes_filtros = request.args.get("CWES")
    cwe_limite = request.args.get("cwe_limit", default=5, type=int)
    categoria_filtro = request.args.get("Categoria")

    if cwes_filtros:
        dic["Titulos"] = [[f'CWE-{cwe}'] for cwe in cwes_filtros.split(",")]

    if not categoria_filtro:
        # Escolher os X mais comuns
        cwes_comuns = consulta_base_de_dados(f"""SELECT V_CWE, COUNT(*) 
                                            FROM VULNERABILITIES_CWE 
                                            LEFT JOIN VULNERABILITIES 
                                            ON VULNERABILITIES.V_ID = VULNERABILITIES_CWE.V_ID
                                            WHERE R_ID IN {lista_r_id} OR "{lista_r_id}" = "('', '')"
                                            GROUP BY VULNERABILITIES_CWE.V_CWE ORDER BY COUNT(*) DESC LIMIT {cwe_limite};""");
        for cwe in cwes_comuns:
            dic["Titulos"].append([f'CWE-{str(cwe[0])}'])

    else:
        cwes_comuns = consulta_base_de_dados(f"""SELECT V_CWE, COUNT(*) 
                                            FROM VULNERABILITIES_CWE 
                                            LEFT JOIN VULNERABILITIES 
                                            ON VULNERABILITIES.V_ID = VULNERABILITIES_CWE.V_ID
                                            JOIN VULNERABILITY_CATEGORY ON VULNERABILITY_CATEGORY.ID_CATEGORY = VULNERABILITIES_CWE.ID_CATEGORY
                                            WHERE VULNERABILITY_CATEGORY.NAME = '{categoria_filtro}' 
                                            WHERE R_ID IN {lista_r_id} OR "{lista_r_id}" = "('', '')"
                                            GROUP BY VULNERABILITIES_CWE.V_CWE ORDER BY COUNT(*) DESC LIMIT {cwe_limite};""");
        for cwe in cwes_comuns:
            dic["Titulos"].append([f'CWE-{str(cwe[0])}'])

    # Fazer a contagem para cada ano
    var_help = []
    for cwe in dic["Titulos"]:
        info = consulta_base_de_dados(f"""SELECT CVE, V_CWE 
                                      FROM VULNERABILITIES 
                                      INNER JOIN VULNERABILITIES_CWE ON VULNERABILITIES_CWE.V_ID = VULNERABILITIES.V_ID 
                                      WHERE VULNERABILITIES_CWE.V_CWE = {cwe[0][4:]} AND (R_ID IN {lista_r_id} OR "{lista_r_id}" = "('', '')");""")
        info_tratada: dict = {
            '1999': 0, '2000': 0, '2001': 0, '2002': 0, '2003': 0, '2004': 0, '2005': 0, 
            '2006': 0, '2007': 0, '2008': 0, '2009': 0, '2010': 0, '2011': 0, '2012': 0,
            '2013': 0, '2014': 0, '2015': 0, '2016': 0, '2017': 0, '2018': 0, '2019': 0,
            '2020': 0, '2021': 0, '2022': 0, '2023': 0, '2024': 0
        }
        
        # Para cada linha adicionamos uma ocorrência em cada ano
        alterou: bool = False
        for linha in info:
            if linha[0] is None:
                continue
            cve = linha[0][4:8]
            info_tratada[cve] += 1
            alterou = True
        
        if alterou:
            dic["Data"].append(info_tratada)
        else:
            var_help.append(cwe)

    for cwe in var_help:
        dic["Titulos"].remove(cwe)
    
    return jsonify(dic)

@bp.route("/find/p_id/", methods=["GET"])
def find_pId():
    """Procuramos o P_ID de uma patch enviado como parâmetro

    Returns:
        dic: data: lista de p_ids encontrados
    """
    dic: dict = {}
    commit = request.args.get("P_ID")
    
    resultados = consulta_base_de_dados(f'SELECT P_ID FROM PATCHES WHERE P_COMMIT = "{commit}";');
    dic["data"] = []
    for linha in resultados:
        dic["data"].append(linha[0])
    
    return jsonify(dic)