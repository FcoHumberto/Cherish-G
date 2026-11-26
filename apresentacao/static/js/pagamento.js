// Campos dinâmicos por forma de pagamento, máscara de CPF (RF21.1) e botão bloqueado até preencher tudo (RF21)
(function () {
  var forma = document.getElementById('forma'), cpf = document.getElementById('cpf'), cartao = document.getElementById('cartao'),
      chave = document.getElementById('chave'), enviar = document.getElementById('enviar');
  function validar() {
    var ok = !!forma.value && cpf.value.replace(/\D/g, '').length === 11;
    if (forma.value === 'cartao') ok = ok && cartao.value.replace(/\D/g, '').length >= 13;
    if (forma.value === 'pix') ok = ok && chave.value.trim().length > 0;
    enviar.disabled = !ok;
  }
  function atualizar() {
    document.querySelectorAll('[data-campo]').forEach(function (l) {
      l.hidden = l.dataset.campo !== forma.value;
      l.querySelector('input').required = !l.hidden;
    });
    enviar.textContent = forma.value === 'cartao' ? 'Realizar pagamento' : 'Prosseguir para o pagamento';
    validar();
  }
  cpf.addEventListener('input', function () {
    var d = cpf.value.replace(/\D/g, '').slice(0, 11);  // só números
    cpf.value = d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    validar();
  });
  cartao.addEventListener('input', function () {
    cartao.value = cartao.value.replace(/\D/g, '').slice(0, 19).replace(/(\d{4})(?=\d)/g, '$1 ');
    validar();
  });
  chave.addEventListener('input', validar);
  forma.addEventListener('change', atualizar);
  atualizar();
})();
