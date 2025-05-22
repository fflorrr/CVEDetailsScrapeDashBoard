// Acontece sempre que a página carrega
window.onload = function() {
    const dropdowns = document.querySelectorAll(".dropdown:not(.grafico)");

    dropdowns.forEach(dropdown => {

        // Vamos buscar os elementos
        const select = dropdown.querySelector('.select');
        const caret = dropdown.querySelector('.caret');
        const menuFilter = dropdown.querySelector('.menuFilter');
        const options = dropdown.querySelectorAll('.menuFilter li');
        const selected = dropdown.querySelector('.selected');
        
        let lista_filtros = [];
        prepare_screen(dropdown);

        // Ao clicar no elemento adicionamoso as classes que permitem que as opções apareçam
        select.addEventListener('click', () => {
            // Certifique-se de que apenas os dropdowns relevantes são manipulados
            select.classList.toggle('select-clicked');
            caret.classList.toggle('caret-rotate');
            menuFilter.classList.toggle('menuFilter-open');
        });

        // Para cada uma que clicamos adicionamos à busca ou removemos
        options.forEach(option => {

            let value = option.dataset.value ? option.dataset.value.trim() : option.innerText.trim();

            if (option.classList.contains("active")){
                lista_filtros.push(value);
            }

            // Listener para todas as opções
            option.addEventListener('click', () => {

                // Sempre que se seleciona uma opção o menu fecha
                select.classList.remove('select-clicked');
                caret.classList.remove('caret-rotate');
                menuFilter.classList.remove('menuFilter-open');

                // Se a opção já tiver ativa removemos, caso contrário adicionamos
                if (option.classList.contains('active')) {
                    option.classList.remove('active');
                    lista_filtros.splice(lista_filtros.indexOf(value), 1);
                } else {

                    // Ao adicionar verificamos se é "ALL", caso seja, removemos todas as outras
                    if (value === "All"){
                        lista_filtros.splice(0, lista_filtros.length);
                        options.forEach(option => {
                            if (option.innerText.trim() !== "All") option.classList.remove('active');
                        })
                    } else {

                        // Se não for "All" temos a certeza que removemos o "All" da lista
                        options.forEach(option => {
                            if (option.innerText.trim() === "All") {
                                option.classList.remove('active');
                                if (lista_filtros.includes("All")){
                                    lista_filtros.splice(lista_filtros.indexOf("All"), 1);
                                }
                                return;
                            }
                        });
                    }
                    
                    // Adicionamos a opção à lista
                    option.classList.add('active');
                    lista_filtros.push(value);
                }

                const activeAfter = dropdown.querySelectorAll('.menuFilter li.active');
                if (activeAfter.length === 0) {
                    const allOpt = Array.from(options).find(opt => opt.innerText.trim() === 'All');
                    allOpt.classList.add('active');
                    lista_filtros = ['All'];
                }

                if (lista_filtros.length > 1){
                    selected.innerText = "Multiple (" + lista_filtros.length + ")";
                } else if (lista_filtros.length < 1) {
                    selected.innerText = "No filter, please select at least one..."
                } else {
                    selected.innerText = lista_filtros[0];
                }

                pesquisaFiltrada();
            });
        });
        let help = dropdown.querySelectorAll('.active');
        console.log(help);
        if (help.length > 1){
            selected.innerText = "Multiple";
        } else if (help.length == 1) {
            let value = help[0].dataset.value ? help[0].dataset.value.trim() : help[0].innerText.trim();
            selected.innerText = value;
        } else {
            selected.innerText = "No filter, please select at least one...";
        }
    });
};

function prepare_screen(param_filter){
    const options = param_filter.querySelectorAll('.menuFilter li');
    let name = param_filter.id;
    let values = get_param_from_url(name);

    if(values.length == 0) {
        values = ['All'];
    }

    options.forEach(option => {
        let val = option.dataset.value?.trim() || option.innerText.trim();
        if (values.includes(val)){
            option.classList.add('active');
        } else {
            option.classList.remove('active');
        }
    });
}

function get_param_from_url(param){
    const url = new URL(window.location.href);
    const raw = url.searchParams.get(param);
    if (raw && raw.trim() !== "") {
        return raw.split(" & ").map(x => x.trim());
    }
    // Retorno vazio
    return [];
}

function pesquisaFiltrada(){

    let [url, search_params] = url_tratamento();

    document.querySelectorAll('.dropdown').forEach(select => {
        // Selção dos valores ativos
        const valores = Array.from(select.querySelectorAll('.active')).map(opt => opt.dataset.value?.trim() || opt.innerText.trim());
        if (valores.length > 0) {
            search_params.set(select.id, valores.join(" & "));
        } else {
            search_params.delete(select.id);
        }
    });

    let cwe_number = document.querySelector('.barraTexto');
    if (cwe_number) {

        // Tratamento da string
        let cwes = cwe_number.value.trim().split(" ");
        // Removemos duplicados e espaços em branco ou vazios
        cwes = cwes.filter((cwe, index) => cwe !== "" && cwe !== " " && cwes.indexOf(cwe) === index);

        search_params.set("CWE", cwes);
    }

    const newUrl = url.toString();

    if (newUrl !== window.location.href) {
        url_atualiza(url, search_params);
    }
}

function url_tratamento(){
    // Obtemos o url e o parametro da pagina e retornamos tudo
    let url = new URL(window.location.href);
    let search_params = url.searchParams;
    let page = Number.parseInt(search_params.get("Page"));
    if (isNaN(page)){
        page = 1;
    }
    return [url, search_params, page];
}

function url_atualiza(url, search_params){
    // Atualizamos o url
    url.search = search_params.toString();
    window.location.href = url.toString();
}
