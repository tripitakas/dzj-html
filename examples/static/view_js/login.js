$('#password').focus(function () {
  $('#psw_info').hide();
});
$('#email').focus(function () {
  $('#psw_info').hide();
});

$('#reset').unbind('click').click(function () {
  $('#psw_info').text('请联系组长或管理员为您重置密码。').show(500);
});

$('form').submit(function (e) {
  e.preventDefault();

  postApi('/user/login', {data: {
    email: $('#email').val(),
    password: $('#password').val()
  }}, function () {
    window.location = next;
  }, function (msg) {
    $('#psw_info').text(msg).show(500);
  });
});