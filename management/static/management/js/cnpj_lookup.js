// Busca os dados da construtora na BrasilAPI ao preencher o CNPJ.
// Marcação esperada: <input name="cnpj" data-cnpj-lookup> no mesmo <form> que
// os campos name, email e phone. Só preenche campos vazios, para não
// sobrescrever o que o usuário digitou. Se a API falhar, o formulário segue normal.
(() => {
  "use strict";

  const API_URL = "https://brasilapi.com.br/api/cnpj/v1/";
  const NAME_MAX_LENGTH = 150;

  // "1123851939" -> "(11) 2385-1939"; "11912345678" -> "(11) 91234-5678"
  function formatPhone(digits) {
    digits = (digits || "").replace(/\D/g, "");
    if (digits.length === 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    if (digits.length === 11) return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
    return "";
  }

  function fillIfEmpty(field, value) {
    if (field && value && !field.value.trim()) field.value = value;
  }

  function setup(input) {
    const form = input.form;
    const status = document.createElement("div");
    status.className = "form-text";
    status.setAttribute("aria-live", "polite");
    input.insertAdjacentElement("afterend", status);

    let lastLookup = "";
    let controller = null;

    function show(message, tone) {
      status.textContent = message;
      status.className = `form-text${tone ? ` text-${tone}` : ""}`;
    }

    async function lookup() {
      const cnpj = input.value.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
      if (cnpj.length !== 14 || cnpj === lastLookup) return;
      lastLookup = cnpj;

      if (controller) controller.abort();
      controller = new AbortController();
      show("Buscando dados do CNPJ…");

      try {
        const response = await fetch(API_URL + cnpj, { signal: controller.signal });
        if (response.status === 404) {
          show("CNPJ não encontrado na Receita Federal. Preencha os dados manualmente.", "warning");
          return;
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const name = (data.nome_fantasia || data.razao_social || "").trim();
        fillIfEmpty(form.elements.name, name.slice(0, NAME_MAX_LENGTH));
        fillIfEmpty(form.elements.email, (data.email || "").toLowerCase());
        fillIfEmpty(form.elements.phone, formatPhone(data.ddd_telefone_1));

        const situation = data.descricao_situacao_cadastral;
        if (situation && situation !== "ATIVA") {
          show(`Atenção: situação cadastral ${situation}.`, "danger");
        } else {
          show("Dados preenchidos a partir da Receita Federal. Confira antes de salvar.", "success");
        }
      } catch (error) {
        if (error.name === "AbortError") return;
        lastLookup = "";
        show("Não foi possível consultar o CNPJ agora. Preencha os dados manualmente.", "warning");
      }
    }

    input.addEventListener("change", lookup);
    input.addEventListener("input", () => {
      // Busca assim que o CNPJ fica completo, sem esperar sair do campo
      if (input.value.replace(/[^A-Za-z0-9]/g, "").length === 14) lookup();
    });
  }

  document.querySelectorAll("[data-cnpj-lookup]").forEach(setup);
})();
