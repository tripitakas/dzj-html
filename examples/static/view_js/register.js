var reg = /^[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$/;

$('#email').focus(function () {
  $('#email_info').hide();
});
$('#password').focus(function () {
  $('#psw_info').hide();
});
$('#confirm_psw').focus(function () {
  $('#confirm_psw_info').hide();
});
$('#password').blur(function () {
  var password = $('#password').val();
  if (!reg.test(password)) {
    $('#psw_info').show();
  }
});
$('#name').focus(function () {
  $('#name_info').hide();
});
$('#school').focus(function () {
  $('#invite_info').hide();
});

$('form').submit(function (e) {
  e.preventDefault();

  var password = $('#password').val();
  var confirm_psw = $('#confirm_psw').val();
  if (password != confirm_psw) {
    $('#confirm_psw_info').show();
    return false;
  }

  var data = {};
  ['name', 'email', 'password', 'school'].forEach(function (key) {
    data[key] = $('#' + key).val();
  });

  postApi('/user/register', {data: data}, function () {
    window.location = next;
  }, function (msg, code) {
    $(code === 1014 ? '#invite_info' :
        code === 1007 ? '#name_info' :
        code === 1003 ? '#email_info' : '#confirm_psw_info').text(msg).show(500);
  });
});