// Sugestões de endereço enquanto digita (RF19) e endereço salvo sempre selecionável
(function () {
  var campo = document.getElementById('endereco'), lista = document.getElementById('sugestoes'), t;
  function buscar() {
    fetch('/api/enderecos?q=' + encodeURIComponent(campo.value)).then(function (r) { return r.json(); }).then(function (itens) {
      lista.innerHTML = '';
      itens.forEach(function (i) { var o = document.createElement('option'); o.value = i; lista.appendChild(o); });
    });
  }
  campo.addEventListener('input', function () { clearTimeout(t); t = setTimeout(buscar, 150); });
  buscar();
  var salvo = document.getElementById('usar-salvo');
  if (salvo) salvo.addEventListener('change', function () { campo.value = salvo.dataset.valor; });
})();
