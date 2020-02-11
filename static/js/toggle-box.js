// 显隐所有框
$('#toggle-boxes').click(function () {
  var active = !$('#toggle-char').hasClass('active');
  $('#toggle-block').toggleClass('active', active);
  $('#toggle-column').toggleClass('active', active);
  $('#toggle-char').toggleClass('active', active);
  $.cut.toggleBox(active, 'block');
  $.cut.toggleBox(active, 'column');
  $.cut.toggleBox(active, 'char');
});

// 显隐栏框
$('#toggle-block').click(function () {
  $(this).toggleClass('active');
  $('rect.block').css('display', $(this).hasClass('active') ? 'block' : 'none');
});

// 显隐列框
$('#toggle-column').click(function () {
  $(this).toggleClass('active');
  $('rect.column').css('display', $(this).hasClass('active') ? 'block' : 'none');
});

// 显隐字框
$('#toggle-char').click(function () {
  $(this).toggleClass('active');
  $('rect.char').css('display', $(this).hasClass('active') ? 'block' : 'none');
});

// 显隐字序
$('#toggle-char-no').click(function () {
  $(this).toggleClass('active');
  $.cut.toggleLabel();
});
