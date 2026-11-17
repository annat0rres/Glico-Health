
  const ctx = document.getElementById('graficoNivelGlicemico').getContext('2d');

  const gradient = ctx.createLinearGradient(0, 0, 0, 180);
  gradient.addColorStop(0, 'rgba(255, 188, 220, 0.6)');
  gradient.addColorStop(1, 'rgba(101, 90, 124, 0.05)');

  const dadosNoHtml = document.getElementById('registros-glicemicos');
  const registros = dadosNoHtml ? JSON.parse(dadosNoHtml.textContent) : [];
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  function criarDadosFiltro(periodo) {
    const limite = new Date(hoje);
    limite.setDate(hoje.getDate() - (periodo === 'dia' ? 0 : periodo === 'semana' ? 6 : 29));

    const registrosFiltrados = registros.filter(registro => {
      const dataRegistro = new Date(`${registro.data}T00:00:00`);
      return dataRegistro >= limite && dataRegistro <= hoje;
    });

    if (periodo === 'dia') {
      return {
        labels: registrosFiltrados.map(registro => registro.hora),
        valores: registrosFiltrados.map(registro => registro.medida)
      };
    }

    return {
      labels: registrosFiltrados.map(registro => {
        const [ano, mes, dia] = registro.data.split('-');
        return `${dia}/${mes}`;
      }),
      valores: registrosFiltrados.map(registro => registro.medida)
    };
  }

  const dadosFiltros = {
    dia: criarDadosFiltro('dia'),
    semana: criarDadosFiltro('semana'),
    mes: criarDadosFiltro('mes')
  };

  Object.values(dadosFiltros).forEach(dados => {
    if (dados.labels.length === 0) {
      dados.labels = ['Sem registros'];
      dados.valores = [null];
    }
  });

  const meuGrafico = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dadosFiltros.dia.labels,
      datasets: [{
        label: 'mg/dL',
        data: dadosFiltros.dia.valores,
        borderColor: '#655A7C',
        borderWidth: 2.5,
        backgroundColor: gradient,
        fill: true,
        tension: 0.45,
        pointRadius: 3,
        pointBackgroundColor: '#655A7C'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#8d829e', font: { size: 11 } } },
        y: { grid: { color: 'rgba(226, 232, 240, 0.6)' }, ticks: { color: '#8d829e', font: { size: 11 } } }
      }
    }
  });

  // botões de filtro
  function filtrarGrafico(periodo, botaoClicado) {
    document.querySelectorAll('.btn-outline-purple').forEach(btn => btn.classList.remove('active'));
    botaoClicado.classList.add('active');
    meuGrafico.data.labels = dadosFiltros[periodo].labels;
    meuGrafico.data.datasets[0].data = dadosFiltros[periodo].valores;
    meuGrafico.update();
  }


  const canvasPeDiabetico = document.getElementById('graficoPeDiabetico');
  if (canvasPeDiabetico) {
  const ctxPeDiabetico = canvasPeDiabetico.getContext('2d');
  const dadosItrNoHtml = document.getElementById('itr-diario');
  const itrDias = dadosItrNoHtml ? JSON.parse(dadosItrNoHtml.textContent) : [];
  const itrValores = itrDias.map(dia => dia.itr);
  const itrCores = itrValores.map(valor => {
    if (valor === null) return 'rgba(190, 190, 190, 0.35)';
    if (valor > 2.2) return 'rgba(255, 188, 220, 0.9)';
    if (valor >= 1.8) return 'rgba(245, 204, 76, 0.9)';
    return 'rgba(101, 90, 124, 0.85)';
  });
  const itrBordas = itrValores.map(valor => {
    if (valor === null) return 'rgba(190, 190, 190, 0.35)';
    if (valor > 2.2) return '#d895b5';
    if (valor >= 1.8) return '#d1aa27';
    return '#655A7C';
  });

  const graficoPeDiabetico = new Chart(ctxPeDiabetico, {
    type: 'bar',
    data: {
      labels: itrDias.map(dia => dia.label),
      datasets: [{
        label: 'ITR (°C)',
        data: itrValores,
        backgroundColor: itrCores,
        borderColor: itrBordas,
        borderWidth: 1,
        borderRadius: 8,
        barThickness: 22
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#8d829e', font: { size: 11 } } },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(226, 232, 240, 0.6)' },
          ticks: { color: '#8d829e', font: { size: 11 } },
          title: { display: true, text: 'ITR (°C)', color: '#8d829e', font: { size: 10 } }
        }
      }
    }
  });

  async function atualizarItrPeDiabetico() {
    try {
      const resposta = await fetch('/home/itr-atualizar');
      if (!resposta.ok) return;

      const dias = await resposta.json();
      const valores = dias.map(dia => dia.itr);
      graficoPeDiabetico.data.labels = dias.map(dia => dia.label);
      graficoPeDiabetico.data.datasets[0].data = valores;
      graficoPeDiabetico.data.datasets[0].backgroundColor = valores.map(valor => {
        if (valor === null) return 'rgba(190, 190, 190, 0.35)';
        if (valor > 2.2) return 'rgba(255, 188, 220, 0.9)';
        if (valor >= 1.8) return 'rgba(245, 204, 76, 0.9)';
        return 'rgba(101, 90, 124, 0.85)';
      });
      graficoPeDiabetico.data.datasets[0].borderColor = valores.map(valor => {
        if (valor === null) return 'rgba(190, 190, 190, 0.35)';
        if (valor > 2.2) return '#d895b5';
        if (valor >= 1.8) return '#d1aa27';
        return '#655A7C';
      });
      graficoPeDiabetico.update();
    } catch (erro) {
      // mantém o último ITR exibido caso o servidor esteja temporariamente indisponível
    }
  }

  atualizarItrPeDiabetico();
  window.setInterval(atualizarItrPeDiabetico, 10000);
  }