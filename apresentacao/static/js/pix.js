// Contagem regressiva de 10 min (RF21.3) e acompanhamento do pagamento
(function () {
  var area = document.getElementById('area-pix'), resta = parseInt(area.dataset.restante, 10), el = document.getElementById('contagem');
  function fmt(s) { return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); }
  setInterval(function () {
    resta = Math.max(0, resta - 1); el.textContent = fmt(resta);
    if (resta === 0) location.href = area.dataset.carrinho;  // o servidor devolve os itens ao carrinho
  }, 1000);
  el.textContent = fmt(resta);
  setInterval(function () {
    fetch(area.dataset.status).then(function (r) { return r.json(); }).then(function (d) {
      if (d.status === 'aprovado') location.href = area.dataset.sucesso;
      if (d.status === 'expirado') location.href = area.dataset.carrinho;
    });
  }, 3000);
  document.getElementById('copiar').addEventListener('click', function () {
    var t = document.getElementById('codigo'); t.select();
    if (navigator.clipboard) navigator.clipboard.writeText(t.value);
  });
})();
