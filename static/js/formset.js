// Adicionar e remover linhas novas em formsets do Django.
// Marcação esperada para um formset com prefixo "facilities":
//   <* id="facilities-body">                  container com uma linha por formulário
//                                              (uma <tr> em tabela, ou qualquer outro elemento)
//   <template id="facilities-empty">          formset.empty_form (com __prefix__)
//   <button data-formset-add="facilities">    adiciona uma linha
//   <button data-formset-remove>              (dentro da linha) remove uma linha nova
// Linhas já salvas usam o checkbox DELETE do Django, não o botão de remover.
(() => {
  "use strict";

  // O Django lê os formulários de 0 a TOTAL_FORMS-1: ao remover uma linha,
  // as seguintes são renumeradas para não deixar buracos
  function renumber(body, prefix, total) {
    const pattern = new RegExp(`${prefix}-(\\d+|__prefix__)-`);
    const rows = [...body.children];
    rows.forEach((row, index) => {
      for (const element of row.querySelectorAll("[name], [id], [for]")) {
        for (const attribute of ["name", "id", "for"]) {
          const value = element.getAttribute(attribute);
          if (value) element.setAttribute(attribute, value.replace(pattern, `${prefix}-${index}-`));
        }
      }
    });
    total.value = String(rows.length);
  }

  for (const button of document.querySelectorAll("[data-formset-add]")) {
    const prefix = button.dataset.formsetAdd;
    const total = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const body = document.getElementById(`${prefix}-body`);
    const template = document.getElementById(`${prefix}-empty`);
    if (!total || !body || !template) continue;

    button.addEventListener("click", () => {
      const index = Number(total.value);
      body.insertAdjacentHTML("beforeend", template.innerHTML.replaceAll("__prefix__", String(index)));
      total.value = String(index + 1);
    });

    body.addEventListener("click", (event) => {
      const remove = event.target.closest("[data-formset-remove]");
      if (!remove) return;
      // Remove o filho direto de body que contém o botão (uma <tr> ou um bloco <div>)
      let row = remove;
      while (row.parentElement !== body) row = row.parentElement;
      row.remove();
      renumber(body, prefix, total);
    });
  }
})();
