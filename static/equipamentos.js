
    "use strict";

    const $ = (seletor) => document.querySelector(seletor);

    const COLUNAS = [
      ["ativo", "Ativo"],
      ["numero_serie", "Número de série"],
      ["categoria", "Categoria"],
      ["status", "Status"],
      ["matricula", "Matrícula"],
      ["data_garantia", "Data de garantia"],
      ["departamento", "Departamento"],
      ["responsavel", "Responsável"],
      ["sede", "Sede"]
    ];

    let versaoInventario = 0;
    let versaoConsulta = 0;
    let versaoExcel = 0;
    let excelPronto = false;
    let importando = false;
    let salvando = false;

    function criar(tag, texto, classe) {
      const item = document.createElement(tag);

      if (texto !== undefined) {
        item.textContent = texto;
      }

      if (classe) {
        item.className = classe;
      }

      return item;
    }

    function mensagem(id, texto, tipo = "") {
      const item = document.getElementById(id);
      item.textContent = texto;
      item.className = `message ${tipo}`.trim();
    }

    function textoErro(erro) {
      return erro instanceof Error
        ? erro.message
        : "Não foi possível concluir a operação.";
    }

    async function api(url, opcoes = {}) {
      if (location.protocol === "file:") {
        throw new Error(
          "Abra o sistema pelo iniciar.bat da pasta controle de ativo. Use o endereço que ele abrir no navegador."
        );
      }

      let resposta;

      try {
        resposta = await fetch(url, {
          cache: "no-store",
          ...opcoes
        });
      } catch {
        throw new Error(
          "Sem conexão com o Python. Confira se o comando python app.py está rodando."
        );
      }

      let dados;

      if (resposta.status === 405 || (resposta.status === 404 && opcoes.method !== 'DELETE')) {
        throw new Error(
          `Este endereço não disponibiliza a API de equipamentos (HTTP ${resposta.status}). Feche esta página, execute iniciar.bat na pasta controle de ativo e use a página aberta por ele. Abrir index.html diretamente ou pelo Live Server não executa o Python.`
        );
      }

      try {
        dados = await resposta.json();
      } catch {
        throw new Error(
          `Resposta inválida do servidor (HTTP ${resposta.status}). Confira o terminal do Python.`
        );
      }

      if (!resposta.ok) {
        throw new Error(
          dados.erro || `Erro no servidor: HTTP ${resposta.status}.`
        );
      }

      return dados;
    }

    function valor(registro, campo) {
      const conteudo = registro[campo];

      if (
        conteudo === null ||
        conteudo === undefined ||
        conteudo === ""
      ) {
        return "—";
      }

      if (
        campo === "data_garantia" &&
        /^\d{4}-\d{2}-\d{2}$/.test(String(conteudo))
      ) {
        return String(conteudo).split("-").reverse().join("/");
      }

      return String(conteudo);
    }

    function linhaVazia(texto) {
      const linha = criar("tr");
      const celula = criar("td", texto);

      celula.colSpan = COLUNAS.length + 1;
      linha.append(celula);

      return linha;
    }

    function renderizarInventario(dados) {
      const corpo = $("#linhas-inventario");
      const fragmento = document.createDocumentFragment();

      $("#total").textContent = dados.registros.length;

      $("#contador-tabela").textContent =
        `${dados.registros.length} equipamento(s)`;

      $("#ultima-atualizacao").textContent =
        dados.ultimo_cadastro || "Sem data registrada";

      if (!dados.registros.length) {
        fragmento.append(
          linhaVazia("Nenhum equipamento cadastrado.")
        );
      } else {
        for (const registro of dados.registros) {
          const linha = criar("tr");

          for (const [campo] of COLUNAS) {
            linha.append(criar("td", valor(registro, campo)));
          }

          const acoes = criar('td');
          const excluir = criar('button', '🗑 Excluir', 'button');
          excluir.type = 'button';
          excluir.title = `Excluir ${registro.ativo} — ${registro.numero_serie}`;
          excluir.setAttribute('aria-label', excluir.title);
          excluir.disabled = !registro.numero_serie;
          excluir.addEventListener('click', async () => {
            if (!window.confirm(`Excluir o equipamento ${registro.ativo}, série ${registro.numero_serie}? Esta ação não pode ser desfeita.`)) return;
            excluir.disabled = true;
            try {
              await api('/api/equipamentos', {method:'DELETE', headers:{'Content-Type':'application/json'}, body:JSON.stringify({numero_serie:registro.numero_serie})});
            } catch (error) {
              mensagem('mensagem-inventario', textoErro(error), 'error');
              excluir.disabled = false;
              return;
            }
            try {
              await carregarInventario();
              limparFicha('Equipamento excluído. Faça uma nova consulta.');
              mensagem('mensagem-inventario', 'Equipamento excluído.', 'success');
            } catch (_) {
              mensagem('mensagem-inventario', 'Equipamento excluído. Clique em Atualizar para recarregar a lista.', 'success');
            }
          });
          acoes.append(excluir);
          linha.append(acoes);

          fragmento.append(linha);
        }
      }

      corpo.replaceChildren(fragmento);
    }

    async function carregarInventario() {
      const versao = ++versaoInventario;

      try {
        const dados = await api("/api/equipamentos");

        if (versao !== versaoInventario) return;

        if (!Array.isArray(dados.registros)) {
          throw new Error("O servidor não retornou uma lista de equipamentos.");
        }

        renderizarInventario(dados);
        mensagem("mensagem-inventario", "");
      } catch (erro) {
        if (versao !== versaoInventario) return;

        $("#contador-tabela").textContent = "Falha ao atualizar";

        mensagem(
          "mensagem-inventario",
          textoErro(erro),
          "error"
        );

        if ($("#total").textContent === "—") {
          $("#linhas-inventario").replaceChildren(
            linhaVazia("Inventário indisponível.")
          );
        }

        throw erro;
      }
    }

    function limparFicha(texto) {
      $("#ficha").replaceChildren(
        criar("div", texto, "empty")
      );

      $("#situacao-ficha").textContent = "Sem seleção";
    }

    function mostrarFicha(registros) {
      const ficha = $("#ficha");
      ficha.replaceChildren();

      if (!registros.length) {
        limparFicha("Número de série não encontrado.");
        return;
      }

      $("#situacao-ficha").textContent =
        `${registros.length} registro(s)`;

      for (const [indice, registro] of registros.entries()) {
        if (registros.length > 1) {
          ficha.append(
            criar(
              "h3",
              `Registro ${indice + 1}`,
              "record-title"
            )
          );
        }

        const lista = criar("dl", undefined, "record-details");

        for (const [campo, titulo] of COLUNAS) {
          const grupo = criar("div");

          grupo.append(
            criar("dt", titulo),
            criar("dd", valor(registro, campo))
          );

          lista.append(grupo);
        }

        ficha.append(lista);
      }
    }

    async function consultarSerie(serie) {
      const versao = ++versaoConsulta;

      limparFicha("Consultando...");
      mensagem("mensagem-consulta", "");

      try {
        const dados = await api(
          `/api/consulta?serie=${encodeURIComponent(serie.trim())}`
        );

        if (versao !== versaoConsulta) return;

        mostrarFicha(dados.registros);

        if (dados.registros.length > 1) {
          mensagem(
            "mensagem-consulta",
            "A série aparece em mais de um registro. Confira as fichas."
          );
        }
      } catch (erro) {
        if (versao !== versaoConsulta) return;

        limparFicha("Consulta indisponível.");

        mensagem(
          "mensagem-consulta",
          textoErro(erro),
          "error"
        );
      }
    }

    $("#form-consulta").addEventListener("submit", async (evento) => {
      evento.preventDefault();

      const serie = $("#serie-consulta").value.trim();
      if (!serie) return;

      const botao = $("#botao-consultar");

      botao.disabled = true;
      botao.textContent = "Consultando...";

      try {
        await consultarSerie(serie);
      } finally {
        botao.disabled = false;
        botao.textContent = "Consultar";
      }
    });

    $("#form-cadastro").addEventListener("submit", async (evento) => {
      evento.preventDefault();

      if (salvando) return;

      const formulario = evento.currentTarget;
      if (!formulario.reportValidity()) return;

      const dados = Object.fromEntries(
        new FormData(formulario)
      );

      for (const campo of Object.keys(dados)) {
        dados[campo] = String(dados[campo]).trim();
      }

      dados.numero_serie = dados.numero_serie.trim();

      if (!dados.ativo || !dados.numero_serie) {
        mensagem(
          "mensagem-cadastro",
          "Preencha o ativo e o número de série.",
          "error"
        );
        return;
      }

      if (dados.data_garantia) {
        const ano = Number(dados.data_garantia.slice(0, 4));

        if (ano < 1000 || ano > 9999) {
          mensagem(
            "mensagem-cadastro",
            "Confira o ano da data de garantia.",
            "error"
          );
          return;
        }
      }

      salvando = true;

      const controles = [
        ...formulario.querySelectorAll("input, select, button")
      ];

      controles.forEach((item) => item.disabled = true);
      $("#salvar").textContent = "Salvando...";

      mensagem("mensagem-cadastro", "Salvando equipamento...");

      try {
        await api("/api/equipamentos", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(dados)
        });

        formulario.reset();

        mensagem(
          "mensagem-cadastro",
          "Equipamento cadastrado.",
          "success"
        );

        versaoConsulta++;
        mostrarFicha([dados]);
        $("#serie-consulta").value = dados.numero_serie;

        try {
          await carregarInventario();
        } catch {
          mensagem(
            "mensagem-cadastro",
            "Equipamento salvo. Clique em Atualizar para recarregar o inventário.",
            "success"
          );
        }
      } catch (erro) {

        mensagem(
          "mensagem-cadastro",
          textoErro(erro),
          "error"
        );
      } finally {
        controles.forEach((item) => item.disabled = false);
        $("#salvar").textContent = "Salvar equipamento";
        salvando = false;
      }
    });

    $("#form-cadastro").addEventListener("reset", () => {
      mensagem("mensagem-cadastro", "");
    });

    $("#atualizar-inventario").addEventListener("click", async () => {
      const botao = $("#atualizar-inventario");

      botao.disabled = true;
      botao.textContent = "Atualizando...";

      try {
        await carregarInventario();
      } catch {

      } finally {
        botao.disabled = false;
        botao.textContent = "Atualizar";
      }
    });

    function dadosExcel(acao) {
      const arquivo = $("#planilha").files[0];

      if (!arquivo) {
        throw new Error("Escolha uma planilha do computador.");
      }

      if (!arquivo.name.toLowerCase().endsWith(".xlsx")) {
        throw new Error("Selecione um arquivo no formato .xlsx.");
      }

      if (arquivo.size > 20 * 1024 * 1024) {
        throw new Error("A planilha deve ter até 20 MB.");
      }

      const dados = new FormData();

      dados.append("arquivo", arquivo);
      dados.append("acao", acao);

      return dados;
    }

    async function visualizarExcel() {
      const versao = ++versaoExcel;
      excelPronto = false;
      $("#botao-importar").disabled = true;
      $("#botao-importar").textContent = "Lendo planilha...";

      mensagem("mensagem-excel", "Lendo a planilha...");

      try {
        const dados = await api("/api/excel", {
          method: "POST",
          body: dadosExcel("visualizar")
        });

        if (versao !== versaoExcel) return;

        $("#resumo-excel").textContent =
          `${dados.quantidade} linha(s) na aba selecionada.`;

        excelPronto = true;
        mensagem("mensagem-excel", "");
      } catch (erro) {
        if (versao !== versaoExcel) return;

        $("#resumo-excel").textContent = "";

        mensagem(
          "mensagem-excel",
          textoErro(erro),
          "error"
        );
      } finally {
        if (versao === versaoExcel) {
          $("#botao-importar").disabled = !excelPronto;
          $("#botao-importar").textContent = "Importar equipamentos";
        }
      }
    }

    $("#planilha").addEventListener("change", () => {
      versaoExcel++;
      excelPronto = false;
      $("#botao-importar").disabled = true;
      $("#botao-importar").textContent = "Importar equipamentos";

      $("#resumo-excel").textContent = "";

      if ($("#planilha").files[0]) {
        visualizarExcel();
      } else {
        mensagem("mensagem-excel", "");
      }
    });

    $("#botao-importar").addEventListener("click", async () => {
      if (importando) return;

      if (!$("#planilha").files[0]) {
        mensagem(
          "mensagem-excel",
          "Escolha uma planilha do computador.",
          "error"
        );
        $("#planilha").focus();
        return;
      }

      if (!excelPronto) {
        // Preserve the actual preview error instead of hiding it with a wait message.
        return;
      }

      let formulario;

      try {
        formulario = dadosExcel("importar");
      } catch (erro) {
        mensagem("mensagem-excel", textoErro(erro), "error");
        return;
      }

      importando = true;

      $("#planilha").disabled = true;
      $("#botao-importar").disabled = true;
      $("#botao-importar").textContent = "Importando...";

      mensagem("mensagem-excel", "Importando equipamentos...");

      try {
        const dados = await api("/api/excel", {
          method: "POST",
          body: formulario
        });

        const resumo =
          `${dados.importados} equipamento(s) importado(s). ` +
          `${dados.ignorados} série(s) já existente(s) ignorada(s).`;

        mensagem("mensagem-excel", resumo, "success");

        try {
          await carregarInventario();
        } catch {
          mensagem(
            "mensagem-excel",
            resumo + " Clique em Atualizar para recarregar o inventário.",
            "success"
          );
        }
      } catch (erro) {
        mensagem("mensagem-excel", textoErro(erro), "error");
      } finally {
        $("#planilha").disabled = false;
        $("#botao-importar").disabled = false;
        $("#botao-importar").textContent = "Importar equipamentos";
        importando = false;
      }
    });


    carregarInventario().catch(() => {});

    let exportando = false;
    let ultimoDownload = null;
    $('#exportar-excel').addEventListener('click', async (event) => {
      event.preventDefault();
      if (exportando) return;
      exportando = true;
      const button = event.currentTarget;
      button.textContent = 'Exportando...';
      button.setAttribute('aria-disabled', 'true');
      mensagem('mensagem-inventario', 'Montando a planilha com todos os dados, sem repetir números de série...');
      try {
        const response = await fetch('/api/excel/exportar', {cache:'no-store'});
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.erro || `Não foi possível exportar (HTTP ${response.status}). Execute iniciar.bat e use o endereço informado pelo Python.`);
        }
        if (!(response.headers.get('Content-Type') || '').includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
          throw new Error('O endereço retornou uma página em vez do Excel. Execute iniciar.bat e use o endereço informado pelo Python.');
        }
        const blob = await response.blob();
        if (ultimoDownload) URL.revokeObjectURL(ultimoDownload);
        const url = URL.createObjectURL(blob);
        ultimoDownload = url;
        const link = document.createElement('a');
        link.href = url; link.download = 'inventario-equipamentos.xlsx';
        document.body.append(link); link.click(); link.remove();
        const total = response.headers.get('X-Export-Registros') || '0';
        const duplicates = response.headers.get('X-Export-Repetidos') || '0';
        const conflicts = Number(response.headers.get('X-Export-Divergencias') || 0);
        mensagem('mensagem-inventario', `${total} equipamento(s) exportado(s). ${duplicates} repetição(ões) consolidada(s).` + (conflicts ? ' Confira os valores diferentes na aba Divergências.' : ''), 'success');
        const manual = criar('a', 'Baixar Excel');
        manual.href = url;
        manual.download = 'inventario-equipamentos.xlsx';
        $('#mensagem-inventario').append(document.createTextNode(' Se o download não iniciou, clique em '), manual);
      } catch (error) {
        mensagem('mensagem-inventario', error instanceof TypeError ? 'Sem conexão com o sistema. Confira se o Python está em execução.' : textoErro(error), 'error');
      } finally {
        exportando = false; button.textContent = 'Exportar Excel'; button.removeAttribute('aria-disabled');
      }
    });
