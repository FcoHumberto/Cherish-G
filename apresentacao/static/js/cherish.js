// Tema claro/noturno (RF36) e utilidades comuns
(function () {
  var raiz = document.documentElement;
  var botao = document.getElementById('tema');
  if (botao) botao.addEventListener('click', function () {
    var novo = raiz.dataset.theme === 'dark' ? 'light' : 'dark';
    raiz.dataset.theme = novo;
    try { localStorage.setItem('cherish-tema', novo); } catch (e) {}
  });

  // Telefone: +XX (XX) XXXXX-XXXX (RF01.1)
  var tel = document.getElementById('telefone');
  if (tel) tel.addEventListener('input', function () {
    var d = tel.value.replace(/\D/g, '').slice(0, 13), s = '';
    if (d.length) s = '+' + d.slice(0, 2);
    if (d.length > 2) s += ' (' + d.slice(2, 4);
    if (d.length >= 4) s += ')';
    if (d.length > 4) s += ' ' + d.slice(4, 9);
    if (d.length > 9) s += '-' + d.slice(9, 13);
    tel.value = s;
  });

  // Confirmação antes de alterar/excluir (RF07 / RN03)
  var dlg = document.getElementById('confirmar');
  document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
    form.addEventListener('submit', function (ev) {
      if (form.dataset.ok) return;
      ev.preventDefault();
      document.getElementById('confirmar-msg').textContent = form.dataset.confirmar;
      dlg.returnValue = '';
      dlg.showModal();
      dlg.onclose = function () {
        if (dlg.returnValue !== 'sim') return;
        var h = document.createElement('input'); h.type = 'hidden'; h.name = 'confirmado'; h.value = 'sim';
        form.appendChild(h); form.dataset.ok = '1'; form.submit();
      };
    });
  });
})();
