let graficoChart = null;
let limiteCWEs = 5;
let lastSearchedCWEs = [];
const colors = ["#B07156", "#413C58", "#EDF060", "#33673B", "#00A6FB", "#FF6B6B", "#6A0572", "#2EC4B6", "#F7B801", "#AECBFA", "#3D348B", "#FF9F1C", "#56E39F", "#A63A50", "#247BA0"]

// Acontece sempre que a página carrega
window.addEventListener("load", function () {
    setupLimite();
    grafico(lastSearchedCWEs);
}, false);

// Limite de CWEs apresentados no gráfico
function setupLimite() {
    const dropdown = document.getElementById("LimiteCWEs");
    const select = dropdown.querySelector(".select");
    const caret = dropdown.querySelector(".caret");
    const menuFilter = dropdown.querySelector(".menuFilter");
    const selected = dropdown.querySelector(".selected");
    const options = dropdown.querySelectorAll(".menuFilter li");

    // Garantir que a primeira opção seja ativa no carregamento
    let activeOption = dropdown.querySelector(".menuFilter li.active");
    if (!activeOption) {
        activeOption = options[0];
        activeOption.classList.add("active");
    }

    // Atualizar o texto exibido no dropdown
    limiteCWEs = parseInt(activeOption.innerText.trim(), 10);
    selected.innerText = activeOption.innerText.trim();

    // Adicionar lógica para abrir/fechar o dropdown
    select.addEventListener("click", () => {
        select.classList.toggle("select-clicked");
        caret.classList.toggle("caret-rotate");
        menuFilter.classList.toggle("menuFilter-open");
    });

    options.forEach(option => {
        option.addEventListener("click", () => {
            // Limpar seleção anterior
            options.forEach(o => o.classList.remove("active"));
            option.classList.add("active");

            // Atualizar limite
            limiteCWEs = parseInt(option.innerText.trim(), 10);
            selected.innerText = limiteCWEs;

            // Fechar o dropdown após a seleção
            select.classList.remove("select-clicked");
            caret.classList.remove("caret-rotate");
            menuFilter.classList.remove("menuFilter-open");

            // Reatualizar gráfico com os últimos CWEs buscados
            grafico(lastSearchedCWEs);
        });
    });
}

// Atualizamos o gráfico quando há uma pesquisa filtrada
function atualizaGrafico(event){
    event.preventDefault();
    let valores = document.querySelector(".barraTexto").value;

    // Divide e filtra CWEs válidos e únicos
    let cwes = valores.trim().split(" ").filter((c, i, arr) => c && /^\d+$/.test(c) && arr.indexOf(c) === i);
    lastSearchedCWEs = cwes;

    // Atualiza o dropdown com o número pesquisado
    const dropdown = document.getElementById("LimiteCWEs");
    const selected = dropdown.querySelector(".selected");
    const options = dropdown.querySelectorAll(".menuFilter li");

    // Atualiza visualmente e internamente o limite
    if (cwes.length > 0) {
        limiteCWEs = cwes.length;

        // Atualiza a interface do dropdown
        options.forEach(opt => {
            if (parseInt(opt.innerText.trim()) === limiteCWEs) {
                opt.classList.add("active");
            } else {
                opt.classList.remove("active");
            }
        });

        // Atualiza o texto visível
        selected.innerText = limiteCWEs;
    }

    // Aplica o limite
    if (cwes.length > limiteCWEs) cwes = cwes.slice(0, limiteCWEs);

    // Atualiza gráfico com os CWEs filtrados
    grafico(cwes);
}

function getUrlParam(){
    // Obtemos o URL
    let queryString = window.location.search;
    // Procuramos pelos parâmetros e retornamos o Projeto
    let urlParams = new URLSearchParams(queryString);
    return urlParams.get("Projeto");
}

function grafico(cwes){

    if (graficoChart) {
        graficoChart.destroy();
    }
    
    // Obtemos o projeto
    const queryString = getUrlParam();
    let url = '/grafico/?Projeto=' + queryString + '&cwe_limit=' + limiteCWEs;
    if (cwes && cwes.length > 0) {
        url += '&CWES=' + cwes.join(',');
    }

    // Pedimos os dados ao flask com o parâmetro
    fetch(url)
    .then(response => {

        if (!response.ok) {
            throw new Error('Erro ao buscar os dados.');
        }
        return response.json();
    })
    .then(data => {

        // Se há CWEs pesquisadas, filtra o que o backend trouxe
        if (lastSearchedCWEs.length > 0) {
            const filteredTitulos = [];
            const filteredData = [];
            const seen = new Set();

            data.Titulos.forEach((tituloArr, idx) => {

                const numero = tituloArr[0].split('-')[1];
                if (lastSearchedCWEs.includes(numero) && !seen.has(numero)) {
                    filteredTitulos.push(tituloArr);
                    filteredData.push(data.Data[idx]);
   
                    seen.add(numero);
                }
            });

            data.Titulos = filteredTitulos;
            data.Data    = filteredData;
        }

        console.log(data);

        // Se não há dados
        if (data.Data.length === 0){
            const ctx = document.getElementById('myChart').getContext('2d');
            ctx.font = '17px "Montserrat", sans-serif';
            ctx.fillStyle = '#00ADB5'
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            // Limpar gráfico
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            // Escrever mensagem
            ctx.fillText('No CWEs found.', ctx.canvas.width / 2, ctx.canvas.height / 2);
            return;
        }

        // {"Data": {Ano: num, Ano: num, Ano: num, etc}, "Titulos": [[],[],[]]}
        let anos = Object.keys(data.Data[0]);

        
        // Onde queremos colocar o gráfico no HTML
        let ctx = document.getElementById('myChart');

        let datasets = data.Titulos.map((titulo, index) => ({
            label: titulo,
            data: Object.values(data.Data[index]),
            borderWidth: 1,
            backgroundColor: colors[index],
            borderColor: colors[index]
        }));

        // Construímos o gráfico
        graficoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: anos,
                datasets: datasets
            },
            options: {
                layout: {
                    padding: 20
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    })
    .catch(error => {
        // Lidamos com possíveis erros
        console.log(error);
    });
}

function download() {
    const originalCanvas = document.getElementById('myChart');
    const width = originalCanvas.width;
    const height = originalCanvas.height;

    // Criar um canvas temporário com as mesmas dimensões
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const tempCtx = tempCanvas.getContext('2d');

    // Desenhar o fundo branco
    tempCtx.fillStyle = 'white';
    tempCtx.fillRect(0, 0, width, height);

    // Desenhar o conteúdo do gráfico original no canvas temporário
    tempCtx.drawImage(originalCanvas, 0, 0);

    // Criar o link para download
    const imageLink = document.createElement('a');
    imageLink.download = 'chart.png';
    imageLink.href = tempCanvas.toDataURL('image/png', 1.0);
    imageLink.click();
}