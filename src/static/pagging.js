// Acontece sempre que a página carrega
window.addEventListener("load",function() {

    // Obtemos o valor do parâmetro "Page" da URL
    let [url, search_params, page] = url_tratamento();
    
    // Atualizamos o texto do link com o valor do parâmetro "Page"
    document.getElementById("numero").textContent = page;
},false);

function url_tratamento(){
    // Obtemos o url e o parametro da pagina e retornamos tudo
    let url = new URL(window.location.href);
    let search_params = url.searchParams;
    let page = Number.parseInt(search_params.get("Page"));

    // Garantir que o valor de "Page" seja válido
    if (isNaN(page) || page < 1) {
        page = 1;
        search_params.set("Page", page);
    }

    return [url, search_params, page];
}

function url_atualiza(url, search_params){
    // Atualizamos o url
    url.search = search_params.toString();
    window.location.href = url.toString();
}

function esquerda(){
    // Atualizamos o valor da pagina no url
    let [url, search_params, page] = url_tratamento();
    if (page > 1){
        search_params.set("Page", page - 1)
    }
    url_atualiza(url, search_params);
}

function direita(){
    // Atualizamos o valor da pagina no url
    let [url, search_params, page] = url_tratamento();
    search_params.set("Page", page + 1)
    url_atualiza(url, search_params);
}

function limita_paginas(offset, limiteOffset) {
    // Atualizamos a transparência das setas e limitamos paginas da tabela
    var setaEsquerda = document.querySelector(".esquerda a");
    var setaDireita = document.querySelector(".direita a");

    let size = 15;

    // Desabilitar seta esquerda para a página 0 e 1
    if (offset <= 1) {
        setaEsquerda.classList.add("desligada");
    } else {
        setaEsquerda.classList.remove("desligada");
    }

    if ((offset + size) > limiteOffset) {
        setaDireita.classList.add("desligada");
    } else {
        setaDireita.classList.remove("desligada");
    }

    // Validar e corrigir o valor da página
    let [url, search_params, page] = url_tratamento();
    let totalPaginas = Math.ceil(limiteOffset / size);

    if (page > totalPaginas) {
        search_params.set("Page", totalPaginas);
        url_atualiza(url, search_params);
    }
}