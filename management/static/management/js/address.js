// Formulário de endereço: lista de municípios por UF e preenchimento pelo CEP (ViaCEP).
// Os campos são encontrados pelo atributo data-address (definido no EstateForm).
(() => {
  "use strict";

  const field = (name) => document.querySelector(`[data-address="${name}"]`);
  const cep = field("cep");
  const state = field("state");
  const city = field("city");
  if (!cep || !state || !city) return;

  const citiesUrl = state.dataset.citiesUrl;

  // Mensagem abaixo do CEP (busca em andamento, CEP não encontrado...)
  const status = document.createElement("div");
  status.className = "form-text";
  cep.insertAdjacentElement("afterend", status);

  const setStatus = (text, isError = false) => {
    status.textContent = text;
    status.classList.toggle("text-danger", isError);
  };

  async function loadCities(uf, selected = "") {
    city.replaceChildren(new Option("---------", ""));
    if (!uf) return;
    city.disabled = true;
    try {
      const response = await fetch(`${citiesUrl}?state=${encodeURIComponent(uf)}`);
      if (!response.ok) throw new Error(response.statusText);
      const data = await response.json();
      for (const { ibge_code, name } of data.cities) {
        city.add(new Option(name, ibge_code, false, String(ibge_code) === String(selected)));
      }
    } catch {
      setStatus("Não foi possível carregar os municípios.", true);
    } finally {
      city.disabled = false;
    }
  }

  async function lookupCep(digits) {
    setStatus("Buscando endereço…");
    try {
      const response = await fetch(`https://viacep.com.br/ws/${digits}/json/`);
      if (!response.ok) throw new Error(response.statusText);
      const data = await response.json();
      if (data.erro) {
        setStatus("CEP não encontrado. Preencha o endereço manualmente.", true);
        return;
      }
      // CEPs gerais de cidades pequenas não trazem logradouro/bairro
      if (data.logradouro) field("street").value = data.logradouro;
      if (data.bairro) field("district").value = data.bairro;
      state.value = data.uf;
      await loadCities(data.uf, data.ibge);
      setStatus("");
      field("number").focus();
    } catch {
      setStatus("Não foi possível consultar o CEP. Preencha o endereço manualmente.", true);
    }
  }

  state.addEventListener("change", () => loadCities(state.value));

  let lastCep = cep.value.replace(/\D/g, "");
  cep.addEventListener("input", () => {
    const digits = cep.value.replace(/\D/g, "");
    if (digits.length === 8 && digits !== lastCep) {
      lastCep = digits;
      lookupCep(digits);
    }
  });
})();
